import numpy as np
from datetime import date
from .formulas import FORMULAS
from db_connect import get_data, check_if_portfolio_exists, save_value


def calc_portfolio_value(bank_id: int,
                         currency: bool,
                         dt: date,
                         formula: str) -> int:
    f_values = np.array(FORMULAS[formula])
    f_signs = np.sign(f_values)
    abs_values = np.abs(f_values)

    data = get_data(bank_id, abs_values, currency, dt)
    data *= f_signs

    return data.sum()


def get_portfolios(bank_ids: list,
                   formulas: list,
                   dates: list,
                   scenario_id: int):
    portfolios = {}

    for bank_id in bank_ids:
        portfolios[bank_id] = {}

        for formula in formulas:
            portfolios[bank_id][formula] = {}
            if formula.endswith('_rub'):
                currency = False
            else:
                currency = True

            t_formula = formula[:-4]

            sums = np.zeros((len(dates)), dtype=np.int64)
            for i, dt in enumerate(dates):
                check = check_if_portfolio_exists(bank_id, dt, scenario_id,
                                                  formula)

                if check is None:
                    value = calc_portfolio_value(bank_id,
                                                 currency,
                                                 dt,
                                                 t_formula)
                    save_value(bank_id, dt, scenario_id, formula, value)
                else:
                    value = check
                sums[i] = value

            portfolios[bank_id][formula]['values'] = sums

    return portfolios
