from django.db import models


class AssistantMessage(models.Model):
    session_id = models.CharField(max_length=255, db_index=True)
    dealer_id = models.IntegerField(null=True, blank=True)
    role = models.CharField(max_length=20)  # user, assistant, system, tool
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session_id", "created_at"]),
        ]

    def __str__(self):
        return f"{self.session_id} - {self.role}: {self.content[:30]}"
