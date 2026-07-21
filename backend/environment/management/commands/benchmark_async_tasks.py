import shutil
import statistics
import time
import uuid
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from rasterio.transform import from_origin

from environment.models import EcologicalIndex, ProcessingTask, RemoteSensingImage
from environment.tasks import calculate_ecological_indices


class Command(BaseCommand):
    help = "Benchmark Redis/Celery NDVI task submission and completion with tiny rasters."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=20)
        parser.add_argument("--timeout", type=int, default=120)

    def handle(self, *args, **options):
        count = options["count"]
        if count < 1:
            raise CommandError("--count must be at least 1.")
        if settings.CELERY_TASK_ALWAYS_EAGER:
            raise CommandError("Set CELERY_TASK_ALWAYS_EAGER=false before benchmarking.")

        records = []
        try:
            for number in range(count):
                token = uuid.uuid4().hex
                relative_path = f"remote_sensing/async_benchmark_{token}.tif"
                image_path = Path(settings.MEDIA_ROOT) / relative_path
                image_path.parent.mkdir(parents=True, exist_ok=True)
                data = np.stack([
                    np.full((4, 4), 100 + band * 20, dtype=np.uint16)
                    for band in range(6)
                ])
                with rasterio.open(
                    image_path,
                    "w",
                    driver="GTiff",
                    width=4,
                    height=4,
                    count=6,
                    dtype="uint16",
                    crs="EPSG:32629",
                    transform=from_origin(500000, 4100000, 10, 10),
                ) as dataset:
                    dataset.write(data)

                image = RemoteSensingImage.objects.create(
                    name=f"async_benchmark_{number}_{token}.tif",
                    image_type="sentinel2",
                    file_path=relative_path,
                    center_lat=34.58,
                    center_lon=105.72,
                    acquisition_date=date.today(),
                    bands_count=6,
                )
                task = ProcessingTask.objects.create(
                    remote_sensing_image=image,
                    task_type="async-benchmark-ndvi",
                    status="pending",
                )
                submitted_at = time.perf_counter()
                celery_task = calculate_ecological_indices.delay(
                    str(image.id), ["ndvi"], str(task.id)
                )
                records.append({
                    "image": image,
                    "task": task,
                    "image_path": image_path,
                    "submit_ms": (time.perf_counter() - submitted_at) * 1000,
                    "celery_task_id": str(celery_task.id),
                })

            deadline = time.monotonic() + options["timeout"]
            while time.monotonic() < deadline:
                unfinished = 0
                for record in records:
                    record["task"].refresh_from_db()
                    if record["task"].status not in {"completed", "failed", "cancelled"}:
                        unfinished += 1
                if unfinished == 0:
                    break
                time.sleep(0.5)

            completed = []
            failed = []
            queue_wait_seconds = []
            processing_seconds = []
            expected_ndvi = (160 - 140) / (160 + 140)
            consistent_count = 0
            for record in records:
                task = record["task"]
                if task.status == "completed":
                    completed.append(task)
                    if task.started_at and task.created_at:
                        queue_wait_seconds.append(
                            (task.started_at - task.created_at).total_seconds()
                        )
                    if task.started_at and task.completed_at:
                        processing_seconds.append(
                            (task.completed_at - task.started_at).total_seconds()
                        )
                    result = EcologicalIndex.objects.get(
                        remote_sensing_image=record["image"], index_type="ndvi"
                    )
                    if abs(result.mean_value - expected_ndvi) < 1e-6:
                        consistent_count += 1
                else:
                    failed.append(task)

            submit_values = [record["submit_ms"] for record in records]
            submit_p95 = sorted(submit_values)[max(0, int(len(submit_values) * 0.95) - 1)]
            summary = {
                "count": count,
                "completed": len(completed),
                "failed_or_timeout": len(failed),
                "success_rate_percent": round(len(completed) / count * 100, 2),
                "submit_avg_ms": round(statistics.mean(submit_values), 2),
                "submit_p95_ms": round(submit_p95, 2),
                "queue_wait_avg_s": round(statistics.mean(queue_wait_seconds), 3) if queue_wait_seconds else None,
                "processing_avg_s": round(statistics.mean(processing_seconds), 3) if processing_seconds else None,
                "ndvi_formula_consistent": f"{consistent_count}/{count}",
            }
            self.stdout.write(str(summary))
            if failed:
                raise CommandError(f"{len(failed)} task(s) did not complete.")
        finally:
            for record in records:
                image = record["image"]
                output_dir = Path(settings.MEDIA_ROOT) / "ecological_indices" / str(image.id)
                image.delete()
                shutil.rmtree(output_dir, ignore_errors=True)
                record["image_path"].unlink(missing_ok=True)
