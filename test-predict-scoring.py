# test file with changes
import os
import sys

def process_data(data):
    results = []
    for item in data:
        if item.get('status') == 'active':
            results.append({
                'id': item['id'],
                'value': item.get('value', 0) * 1.5,
                'processed': True
            })
    return results
