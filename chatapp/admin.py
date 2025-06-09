from django.contrib import admin
from .models import ChatSession, ChatMessage

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'document', 'created_at']
    actions = ['cleanup_duplicates']
    
    def cleanup_duplicates(self, request, queryset):
        from django.db.models import Count
        
        # Find duplicates
        duplicates = ChatSession.objects.values('user_id', 'document_id').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        moved_messages = 0
        deleted_sessions = 0
        
        # Process duplicates
        for dup in duplicates:
            sessions = ChatSession.objects.filter(
                user_id=dup['user_id'],
                document_id=dup['document_id']
            ).order_by('-created_at')
            
            keep_session = sessions.first()
            
            # Process each duplicate
            for session in sessions[1:]:
                # Move messages
                msg_count = ChatMessage.objects.filter(session=session).update(session=keep_session)
                moved_messages += msg_count
                
                # Delete session
                session.delete()
                deleted_sessions += 1
        
        self.message_user(
            request,
            f'Cleaned up {deleted_sessions} duplicate sessions, moved {moved_messages} messages.'
        )
    
    cleanup_duplicates.short_description = "Clean up duplicate sessions"
