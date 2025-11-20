import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text

engine = create_engine('postgresql://job_pricing_user:change_this_secure_password_123@localhost:5432/tria_db')
conn = engine.connect()
result = conn.execute(text('''
    SELECT o.id, o.outlet_id, out.name, o.status, o.total_amount, o.created_at
    FROM orders o
    LEFT JOIN outlets out ON o.outlet_id = out.id
    ORDER BY o.created_at DESC
    LIMIT 5
'''))

print('Recent Orders:')
print('=' * 100)
for row in result:
    print(f'Order {row[0]}: {row[2]} (Outlet ID {row[1]})')
    print(f'  Status: {row[3]}, Total: ${row[4]:.2f}, Created: {row[5]}')
    print()
