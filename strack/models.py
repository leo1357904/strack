from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import FileExtensionValidator

class AssemblyCode(models.Model):
    title = models.CharField(max_length=50)
    file_prefix = models.CharField(max_length=50)
    code_file = models.FileField(validators=[FileExtensionValidator(['c'], 'Please upload a C file with File extension "c".')])
    code_text = models.TextField(default="")
    # executable_file = models.FileField()
    state_file = models.FileField()
    creation_time = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return f"AssemblyCode(id={str(self.id)}, title={self.title}, file_prefix: {self.file_prefix}, code_text={self.code_text}, creation_time={self.creation_time})"

class Profile(models.Model):
    profile_id    = models.IntegerField(primary_key=True)
    bio_content   = models.CharField(max_length=200)
    picture       = models.FileField(blank=True)
    content_type  = models.CharField(max_length=50)
    created_by    = models.OneToOneField(User, on_delete=models.PROTECT)
    creation_time = models.DateTimeField()
    update_time   = models.DateTimeField()
    following     = models.ManyToManyField(User, related_name="followers")
    starring      = models.ManyToManyField(AssemblyCode, related_name="starred")

    def __str__(self):
        return f"Profile(profile_id={str(self.profile_id)}, post_content={self.bio_content}, picture: {self.picture}, creation_time={str(self.creation_time)}, update_time={self.update_time})"
