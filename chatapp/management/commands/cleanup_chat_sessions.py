# Create a file at chatapp/management/commands/cleanup_chat_sessions.py

from django.core.management.base import BaseCommand
from django.db.models import Count
from chatapp.models import ChatSession, ChatMessage
import logging

class Command(BaseCommand):
    help = 'Clean up duplicate ChatSession records, preserving messages'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Perform a dry run without making actual changes',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write('Running in DRY RUN mode - no changes will be made')
        
        # 1. Find duplicates
        self.stdout.write('Finding duplicate chat sessions...')
        duplicates = ChatSession.objects.values('user_id', 'document_id').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        self.stdout.write(f'Found {len(duplicates)} sets of duplicate sessions')
        
        total_moved = 0
        total_deleted = 0
        
        # 2. Process each duplicate set
        for dup in duplicates:
            user_id = dup['user_id']
            doc_id = dup['document_id']
            
            sessions = ChatSession.objects.filter(
                user_id=user_id,
                document_id=doc_id
            ).order_by('-created_at')  # Most recent first
            
            keep_session = sessions.first()
            session_ids = [s.id for s in sessions]
            
            self.stdout.write(
                f'Processing duplicate sessions {session_ids} ' +
                f'for user:{user_id}, document:{doc_id}'
            )
            self.stdout.write(f'Keeping session {keep_session.id}')
            
            # Process each duplicate
            for session in sessions[1:]:
                # Count and move messages
                messages = ChatMessage.objects.filter(session=session)
                msg_count = messages.count()
                
                if msg_count > 0:
                    self.stdout.write(f'  - Moving {msg_count} messages from session {session.id}')
                    if not dry_run:
                        messages.update(session=keep_session)
                        total_moved += msg_count
                
                # Delete the session
                self.stdout.write(f'  - Deleting session {session.id}')
                if not dry_run:
                    session.delete()
                    total_deleted += 1
        
        # Summary
        status = '[DRY RUN] Would have' if dry_run else 'Successfully'
        self.stdout.write(self.style.SUCCESS(
            f'{status} moved {total_moved} messages and deleted {total_deleted} duplicate sessions'
        ))