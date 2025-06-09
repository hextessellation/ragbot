from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django import forms
from .models import Document

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('email',)

class DocumentUploadForm(forms.ModelForm):
    file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'accept': '.pdf,.docx,.xlsx,.csv,.txt,.md,.json,.xml'})
    )
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10}),
        required=False,
        help_text="You can either upload a file or paste content here"
    )
    
    class Meta:
        model = Document
        fields = ['title', 'file', 'content']
    
    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('file')
        content = cleaned_data.get('content')
        
        # Ensure either file or content is provided
        if not file and not content:
            raise forms.ValidationError("You must either upload a file or provide content")
        
        return cleaned_data
