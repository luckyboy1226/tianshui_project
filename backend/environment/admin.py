from django.contrib import admin

from .models import (
    CitizenFeedback,
    ClimateAnalysisResult,
    ClimateDataFile,
    BusinessLayer,
    BusinessLayerAuditLog,
    EcologicalIndex,
    EcologicalIndexFile,
    EcologicalProjectFile,
    OverlayAnalysisTask,
    ProcessingTask,
    RemoteSensingImage,
    RSEIResult,
)


@admin.register(CitizenFeedback)
class CitizenFeedbackAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'contact', 'created_by', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'content', 'contact')
    readonly_fields = ('id', 'created_at', 'created_by')
    ordering = ('-created_at',)


@admin.register(ProcessingTask)
class ProcessingTaskAdmin(admin.ModelAdmin):
    list_display = ('task_type', 'status', 'progress', 'current_step', 'created_by', 'created_at')
    list_filter = ('status', 'task_type', 'created_at')
    search_fields = ('task_type', 'current_step', 'error_message')
    readonly_fields = ('id', 'created_at', 'started_at', 'completed_at')
    ordering = ('-created_at',)


@admin.register(RemoteSensingImage)
class RemoteSensingImageAdmin(admin.ModelAdmin):
    list_display = ('name', 'image_type', 'bands_count', 'processing_status', 'uploaded_by', 'processing_date')
    list_filter = ('image_type', 'processing_status', 'processing_date')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'processing_date')
    ordering = ('-processing_date',)


@admin.register(EcologicalIndex)
class EcologicalIndexAdmin(admin.ModelAdmin):
    list_display = ('remote_sensing_image', 'index_type', 'mean_value', 'created_at')
    list_filter = ('index_type', 'created_at')
    search_fields = ('remote_sensing_image__name', 'index_type')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(RSEIResult)
class RSEIResultAdmin(admin.ModelAdmin):
    list_display = ('remote_sensing_image', 'pc1_variance', 'created_at')
    search_fields = ('remote_sensing_image__name',)
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)


@admin.register(ClimateDataFile)
class ClimateDataFileAdmin(admin.ModelAdmin):
    list_display = ('name', 'file_type', 'status', 'uploaded_by', 'created_at', 'processed_at')
    list_filter = ('file_type', 'status', 'created_at')
    search_fields = ('name', 'description', 'error_message')
    readonly_fields = ('id', 'created_at', 'processed_at')
    ordering = ('-created_at',)


@admin.register(ClimateAnalysisResult)
class ClimateAnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('data_file', 'analysis_type', 'temperature_avg', 'precipitation_avg', 'created_at')
    list_filter = ('analysis_type', 'created_at')
    search_fields = ('data_file__name',)
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)


@admin.register(BusinessLayer)
class BusinessLayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'layer_type', 'source_format', 'status', 'geoserver_layer_name', 'uploaded_by', 'created_at')
    list_filter = ('layer_type', 'source_format', 'status', 'created_at')
    search_fields = ('name', 'description', 'geoserver_layer_name', 'error_message')
    readonly_fields = ('id', 'created_at', 'updated_at', 'published_at')
    ordering = ('-created_at',)


@admin.register(BusinessLayerAuditLog)
class BusinessLayerAuditLogAdmin(admin.ModelAdmin):
    list_display = ('business_layer', 'action', 'status', 'operator_name', 'created_at')
    list_filter = ('action', 'status', 'created_at')
    search_fields = ('business_layer__name', 'operator_name', 'message')
    readonly_fields = ('id', 'business_layer', 'action', 'status', 'operator', 'operator_name', 'message', 'details', 'created_at')
    ordering = ('-created_at',)


@admin.register(EcologicalIndexFile)
class EcologicalIndexFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'status', 'uploaded_by', 'created_at', 'processed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('filename', 'description', 'error_message')
    readonly_fields = ('id', 'created_at', 'processed_at')
    ordering = ('-created_at',)


@admin.register(EcologicalProjectFile)
class EcologicalProjectFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'status', 'uploaded_by', 'created_at', 'processed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('filename', 'description', 'error_message')
    readonly_fields = ('id', 'created_at', 'processed_at')
    ordering = ('-created_at',)


@admin.register(OverlayAnalysisTask)
class OverlayAnalysisTaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'progress', 'overall_risk_level', 'created_by', 'created_at')
    list_filter = ('status', 'overall_risk_level', 'created_at')
    search_fields = ('name', 'description', 'error_message')
    readonly_fields = ('id', 'created_at', 'started_at', 'completed_at')
    ordering = ('-created_at',)
