create_table = """
CREATE TABLE company(
   ID INT PRIMARY KEY     NOT NULL,
   NAME           TEXT    NOT NULL,
   AGE            INT     NOT NULL,
   ADDRESS        CHAR(50),
   SALARY         REAL
);
"""

create_entries = """
INSERT INTO company VALUES (1, 'john', 24, '123 mulberry lane', 123)
"""

# process_name is put into user_ns
from sqlalchemy import create_engine
# engine will be accessed to run submission
connect('sqlite', "")

self.conn.execute(create_table)
self.conn.execute(create_entries)
