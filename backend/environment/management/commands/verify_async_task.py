import shutil
import time
import uuid
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from rasterio.transform import from_origin

from environment.models import ProcessingTask, RemoteSensingImage
from environment.tasks import calculate_ecological_indices


class Command(BaseCommand):
    help = "Verify the Redis and Celery ecological-index task flow with a tiny raster."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=30)

    def handle(self, *args, **options):
        if settings.CELERY_TASK_ALWAYS_EAGER:
            raise CommandError("Set CELERY_TASK_ALWAYS_EAGER=false before running this check.")

        token = uuid.uuid4().hex
        relative_path = f"remote_sensing/async_smoke_{token}.tif"
        image_path = Path(settings.MEDIA_ROOT) / relative_path
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image = None

        try:
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
                name=f"async_smoke_{token}.tif",
                image_type="sentinel2",
                file_path=relative_path,
                center_lat=34.58,
                center_lon=105.72,
                acquisition_date=date.today(),
                bands_count=6,
            )
            task = ProcessingTask.objects.create(
                remote_sensing_image=image,
                task_type="async-smoke-ndvi",
                status="pending",
            )
            celery_task = calculate_ecological_indices.delay(
                str(image.id), ["ndvi"], str(task.id)
            )
            self.stdout.write(f"submitted task_id={task.id} celery_task_id={celery_task.id}")

            deadline = time.monotonic() + options["timeout"]
            while time.monotonic() < deadline:
                task.refresh_from_db()
                if task.status in {"completed", "failed", "cancelled"}:
                    break
                time.sleep(0.5)

            task.refresh_from_db()
            if task.status != "completed":
                raise CommandError(
                    f"Task ended with status={task.status}, error={task.error_message!r}"
                )
            self.stdout.write(self.style.SUCCESS("Async Celery task completed successfully."))
        finally:
            if image:
                output_dir = Path(settings.MEDIA_ROOT) / "ecological_indices" / str(image.id)
                image.delete()
                shutil.rmtree(output_dir, ignore_errors=True)
            image_path.unlink(missing_ok=True)
