from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now

class Document(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)  # Make content optional for file-only uploads
    file = models.FileField(upload_to='documents/', blank=True, null=True)
    file_type = models.CharField(max_length=10, blank=True)  # To store file extension
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Existing fields for tracking document processing
    is_processed = models.BooleanField(default=False)
    chunks = models.IntegerField(default=0)
    processing_error = models.TextField(blank=True, null=True)
    last_processed = models.DateTimeField(null=True, blank=True)
    processing_status = models.CharField(max_length=100, blank=True, null=True)  # New field for processing status
    
    def __str__(self):
        return self.title
    
    def get_file_extension(self):
        if self.file:
            return self.file.name.split('.')[-1].lower()
        return None
    
    def save(self, *args, **kwargs):
        # Set file_type when saving if file is present
        if self.file:
            self.file_type = self.get_file_extension()
        super().save(*args, **kwargs)

class ChatSession(models.Model):
    # Add fields to track session state and persistent memory
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    document = models.ForeignKey('Document', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    memory_key_points = models.JSONField(blank=True, null=True)
    
    # Method to update session memory with key information
    def update_memory(self, key_points):
        if not self.memory_key_points:
            self.memory_key_points = {}
        
        # Update memory with new key points
        self.memory_key_points.update(key_points)
        self.save()
    
    def __str__(self):
        return f"Chat session {self.id} - User: {self.user.username}, Doc: {self.document.title}"

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    is_user = models.BooleanField(default=True)  # True if message is from user, False if from AI
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
