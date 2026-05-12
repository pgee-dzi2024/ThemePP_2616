import csv
import io
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


def parse_emails_from_csv(file_obj):
    """
    Чете CSV файл и връща:
    - valid_emails: списък с валидни имейли
    - invalid_entries: списък с грешни записи
    """
    try:
        decoded_file = file_obj.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        decoded_file = file_obj.read().decode('cp1251')

    file_io = io.StringIO(decoded_file)
    reader = csv.reader(file_io)

    valid_emails = []
    invalid_entries = []
    total_rows = 0

    for row in reader:
        total_rows += 1

        if not row:
            invalid_entries.append({
                'row': total_rows,
                'value': '',
                'error': 'Празен ред'
            })
            continue

        raw_value = row[0].strip()

        if not raw_value:
            invalid_entries.append({
                'row': total_rows,
                'value': '',
                'error': 'Празна стойност'
            })
            continue

        try:
            validate_email(raw_value)
            valid_emails.append(raw_value.lower())
        except ValidationError:
            invalid_entries.append({
                'row': total_rows,
                'value': raw_value,
                'error': 'Невалиден имейл адрес'
            })

    valid_emails = list(dict.fromkeys(valid_emails))

    return {
        'total_rows': total_rows,
        'valid_emails': valid_emails,
        'invalid_entries': invalid_entries,
    }