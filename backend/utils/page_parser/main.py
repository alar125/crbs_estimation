from os import cpu_count, getenv
from datetime import date
from parse import parse_to_db
from multiprocessing import Pool
from functools import partial
from psycopg2 import connect
from tqdm import tqdm

if __name__ == '__main__':
    dates = [date(y, m, 1) for y in range(2016, 2021) for m in [1, 4, 7, 10]]

    connection = connect(f'dbname={getenv("DB_NAME")} '
                         f'user={getenv("DB_USER")} '
                         f'password={getenv("DB_PASSWORD")} '
                         f'user={getenv("DB_USER")}')

    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT id
        FROM bank
        '''
    )
    banks = list(map(lambda x: x[0], cursor.fetchall()))
    connection.close()

    # У разных форм разные поля, так что надо исправлять :(
    # forms = [(101, 13, [0, 10, 11]), (135, 2, [0, 1])]
    forms = [(101, 13, [0, 10, 11])]

    with Pool(processes=cpu_count()) as pool:
        for form, column_count, target_columns in forms:
            for d in tqdm(dates):
                print(f'Parsing form {form} for date {d}')
                pool.map(partial(parse_to_db, d=d, form=form,
                                 target_columns=target_columns,
                                 column_count=column_count), banks)
