from django import forms

from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'autofocus': True}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }
        error_messages = {'name': {'required': 'Escribe el nombre del proyecto.'}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if self.is_bound and name in self.errors:
                field.widget.attrs.update({
                    'class': 'form-control is-invalid',
                    'aria-invalid': 'true',
                    'aria-describedby': f'id_{name}_errors',
                })
