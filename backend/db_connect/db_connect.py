import numpy as np
from os import getenv, cpu_count
from psycopg2 import connect
from datetime import date
from multiprocessing.pool import ThreadPool
from functools import partial


def get_data(bank_id: int,
             account_ids: np.ndarray,
             currency: bool,
             dt: date) -> np.ndarray:
    conn = connect(f'user={getenv("DB_USER")} '
                   f'dbname={getenv("DB_NAME")} '
                   f'password={getenv("DB_PASSWORD")} '
                   f'host={getenv("DB_HOST")}')

    cur = conn.cursor()

    if currency:
        suffix = '_currency'
    else:
        suffix = '_ruble'

    values = np.zeros_like(account_ids, dtype=np.int64)

    for i, account_id in enumerate(account_ids):
        cur.execute(
            f'''
            SELECT val{suffix}
            FROM form_101
            WHERE bank_id = %s AND dt = %s AND account = %s
            ''',
            (bank_id, dt, int(account_id))
        )
        a = cur.fetchone()
        if a is None:
            a = 0
        else:
            a = a[0]
        values[i] = a

    return values


def get_all_banks() -> list:
    conn = connect(f'user={getenv("DB_USER")} '
                   f'dbname={getenv("DB_NAME")} '
                   f'password={getenv("DB_PASSWORD")} '
                   f'host={getenv("DB_HOST")}')
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT id, name
                FROM bank
                '''
            )
            a = cur.fetchall()

    conn.close()

    return a


def get_macro_indicators(dates: list,
                         macro_name: str,
                         scenario_id: int) -> np.ndarray:
    conn = connect(f'user={getenv("DB_USER")} '
                   f'dbname={getenv("DB_NAME")} '
                   f'password={getenv("DB_PASSWORD")} '
                   f'host={getenv("DB_HOST")}')
    cur = conn.cursor()

    values = np.zeros(len(dates), dtype=np.float32)

    for i, dt in enumerate(dates):
        cur.execute(
            '''
            SELECT val
            FROM scenario_value JOIN macro_indicator ON
                macro_indicator.id = scenario_value.macro_id
            WHERE scenario_value.dt = %s AND
                  scenario_value.scenario_id = %s AND 
                  macro_indicator.name_eng = %s
            ''',
            (dt, scenario_id, macro_name)
        )
        a = cur.fetchone()
        if a is None:
            a = 0
        else:
            a = a[0]
        values[i] = a

    return values


def get_indicator_values(dates, indicator_names, scenario_id):
    with ThreadPool(cpu_count()) as p:
        indicators = p.map(
            partial(get_macro_indicators,
                    dates,
                    scenario_id=scenario_id),
            indicator_names
        )
    return np.asarray(indicators)


def get_modeling_indicators(dates, indicator_names, scenario_id):
    with ThreadPool(cpu_count()) as p:
        indicators = p.map(
            partial(get_macro_indicators,
                    dates,
                    scenario_id=scenario_id),
            indicator_names
        )
    return np.asarray(indicators)


def get_macro_names():
    conn = connect(f'user={getenv("DB_USER")} '
                   f'dbname={getenv("DB_NAME")} '
                   f'password={getenv("DB_PASSWORD")} '
                   f'host={getenv("DB_HOST")}')
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT name_eng
        FROM macro_indicator
        '''
    )
    a = list(map(lambda x: x[0], cur.fetchall()))
    return a


def get_min_date():
    conn = connect(f'user={getenv("DB_USER")} '
                   f'dbname={getenv("DB_NAME")} '
                   f'password={getenv("DB_PASSWORD")} '
                   f'host={getenv("DB_HOST")}')
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT min(dt)
                FROM form_101
                '''
            )
            a = cur.fetchone()

    conn.close()

    return a[0] if len(a) > 0 else None


def check_if_model_exists(calc_date, bank_id, m_horizon, h_horizon,
                          scenario_id, indicator_id):
    conn = connect(f'user={getenv("DB_USER")} '
                   f'dbname={getenv("DB_NAME")} '
                   f'password={getenv("DB_PASSWORD")} '
                   f'host={getenv("DB_HOST")}')

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT val
                FROM calc_result
                         JOIN (
                    SELECT calc_id, calc_date
                    FROM calc_parameters
                    WHERE calc_date = %s
                      AND bank_id = %s
                      AND m_horizon = %s
                      AND h_horizon = %s
                      AND scenario_id = %s
                    ORDER BY calc_date, calc_id DESC
                    LIMIT 1
                ) AS t1 ON calc_id = calc_result.id
                WHERE ind_id = %s
                ORDER BY dt;
                ''',
                (calc_date, bank_id,
                 m_horizon, h_horizon,
                 scenario_id, indicator_id)
            )
            results = cur.fetchall()

    conn.close()

    return results


def get_calc_results(calc_id, m_dates):
    conn = connect(f'user={getenv("DB_USER")} '
                   f'dbname={getenv("DB_NAME")} '
                   f'password={getenv("DB_PASSWORD")} '
                   f'host={getenv("DB_HOST")}')
    values = []

    with conn:
        with conn.cursor() as cur:
            for dt in m_dates:
                cur.execute(
                    '''
                    SELECT val
                    FROM calc_result
                    WHERE id = %s AND dt = %s
                    ''', (calc_id, dt)
                )
                values.append(cur.fetchone()[0])
    conn.close()

    return values


def check_if_portfolio_exists(bank_id, dt, scenario_id, ind_name):
    conn = connect(f'user={getenv("DB_USER")} '
                   f'dbname={getenv("DB_NAME")} '
                   f'password={getenv("DB_PASSWORD")} '
                   f'host={getenv("DB_HOST")}')
    ind_id = get_bank_indicator(ind_name)

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT val
                FROM historical_portfolios
                WHERE bank_id = %s AND 
                      dt = %s AND 
                      scenario_id = %s AND 
                      ind_id = %s
                ''', (bank_id, dt, scenario_id, ind_id)
            )
            a = cur.fetchone()
    conn.close()

    if a is not None:
        a = a[0]

    return a


def save_modeling_value(calc_id, dt, ind_id, value):
    conn = connect(f'user={getenv("DB_USER")} '
                   f'dbname={getenv("DB_NAME")} '
                   f'password={getenv("DB_PASSWORD")} '
                   f'host={getenv("DB_HOST")}')
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO calc_result (id, dt, val, ind_id)
                VALUES (%s, %s, %s, %s)
                ''', (calc_id, dt, float(value), ind_id)
            )
    conn.close()


def get_bank_indicator(ind_name):
    conn = connect(f'user={getenv("DB_USER")} '
                   f'dbname={getenv("DB_NAME")} '
                   f'password={getenv("DB_PASSWORD")} '
                   f'host={getenv("DB_HOST")}')
    with conn:
        with conn.cursor() as cur:
            # Get indicator id
            cur.execute(
                '''
                SELECT id
                FROM bank_indicator
                WHERE name_eng = %s
                ''', (ind_name,)
            )
            ind_id = cur.fetchone()[0]

    return ind_id


def save_modeling_values(bank_id, calc_date, m_horizon, h_horizon, scenario_id,
                         ind_names, values, m_dates):
    conn = connect(f'user={getenv("DB_USER")} '
                   f'dbname={getenv("DB_NAME")} '
                   f'password={getenv("DB_PASSWORD")} '
                   f'host={getenv("DB_HOST")}')
    with conn:
        with conn.cursor() as cur:
            # Get indicator id
            cur.execute(
                '''
                INSERT INTO calc_parameters (calc_date, bank_id,
                                             m_horizon, h_horizon,
                                             scenario_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING calc_id
                ''',
                (calc_date, bank_id, m_horizon, h_horizon, scenario_id)
            )
            calc_id = cur.fetchone()[0]
            conn.commit()

            for ind_name, value in zip(ind_names, values):
                # logging.warning(f'Ind_name: {ind_name}')
                # logging.warning(f'Value: {value}')

                ind_id = get_bank_indicator(ind_name)
                # logging.warning(f'Ind id: {ind_id}')

                for dt, v in zip(m_dates, value):
                    save_modeling_value(calc_id, dt, ind_id, v)

    conn.close()


def save_value(bank_id, dt, scenario_id, ind_name, value):
    conn = connect(f'user={getenv("DB_USER")} '
                   f'dbname={getenv("DB_NAME")} '
                   f'password={getenv("DB_PASSWORD")} '
                   f'host={getenv("DB_HOST")}')
    ind_id = get_bank_indicator(ind_name)

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO historical_portfolios
                VALUES (%s, %s, %s, %s, %s)
                ''', (dt, scenario_id, ind_id, bank_id, float(value))
            )
    conn.close()
