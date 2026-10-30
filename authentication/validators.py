import re

from django.core.exceptions import ValidationError


class SpecialCharacterValidator:
    def validate(self, password, user=None):
        if not re.search(r'[^A-Za-z0-9]', password):
            raise ValidationError(
                'Password harus mengandung minimal satu karakter khusus.',
                code='password_no_special_character',
            )

    def get_help_text(self):
        return 'Password harus mengandung minimal satu karakter khusus.'