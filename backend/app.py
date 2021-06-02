import base64
import json
import numpy as np
from utils import get_template, parse_to_db
from flask import Flask, request, Response
from db_connect import (get_macro_indicators,
                        get_indicator_values,
                        get_macro_names,
                        get_all_banks,
                        get_min_date,
                        check_if_model_exists,
                        save_modeling_values,
                        save_modeling_value)
from credit_risk import (get_portfolios,
                         get_dates,
                         get_modeling_dates,
                         get_bank_stats,
                         get_varmax_predictions,
                         get_predictions,
                         convert_arrays_to_lists,
                         check_data,
                         check_cointegration,
                         make_predictions,
                         make_checks_and_correlations,
                         make_stationary,
                         TARGET_FORMULAS,
                         ModelType)
from datetime import date

app = Flask(__name__)


@app.route('/macro', methods=['POST'])
def macro():
    r = request.values

    m_horizon: int = json.loads(r['m_horizon'])
    calc_date: date = date.fromisoformat(json.loads(r['calc_date']))

    result = {}

    min_h_date = get_min_date()

    # Get calculation dates range
    dates = get_dates(min_h_date, calc_date)

    # Modeling horizon dates
    m_dates = get_modeling_dates(m_horizon, calc_date)

    macro_list = get_macro_names()

    h_indicators = get_indicator_values(
        dates=dates,
        indicator_names=macro_list,
        scenario_id=1
    )

    for i, (name, indicator) in enumerate(zip(macro_list, h_indicators)):
        # _, counts = make_stationary(np.asarray([indicator]))
        left = h_indicators[:i]
        left_names = macro_list[:i]
        if i == len(h_indicators) - 1:
            target_indicators = left
            target_names = left_names
        else:
            target_indicators = np.concatenate((left, h_indicators[i + 1:]))
            target_names = left_names + macro_list[i + 1:]

        _, _, p_counts, _, correlations, model_type = check_data(
            portfolios=np.asarray([indicator]),
            scenarios=target_indicators,
            scenario_names=target_names
        )

        result[name] = {
            'values': indicator,
            'stationary_counts': p_counts[0],
            'correlations': correlations,
            'correlation_values': get_indicator_values(dates, correlations, 1),
            'm_correlation_values': get_indicator_values(m_dates, correlations,
                                                         2),
            'model_type': model_type
        }

    for name, values in result.items():
        if values['model_type'] == ModelType.varmax:
            target_indicators = []
            target_names = []
            target_correlations = [values['correlations']]

            for t_name, t_values in result.items():
                if t_name == name:
                    continue
                target_indicators.append(t_values['values'])
                target_names.append(t_name)
                target_correlations.append(t_values['correlations'])

            cointegrations = check_cointegration(
                np.asarray([values['values']]),
                np.asarray(target_indicators),
                target_names
            )

            if len(cointegrations) <= 1:
                values['model_type'] = ModelType.arima
                continue

            intersect = set.intersection(
                *[set(s) for s in target_correlations]
            )
            if len(intersect) <= 1:
                values['model_type'] = ModelType.arima
                continue

            corr_indicators = get_indicator_values(
                dates=dates,
                indicator_names=list(intersect),
                scenario_id=1
            )
            m_corr_indicators = get_indicator_values(
                dates=m_dates,
                indicator_names=list(intersect),
                scenario_id=2
            )
            values['correlation_values'] = corr_indicators
            values['m_correlation_values'] = m_corr_indicators

            get_varmax_predictions(result, name, cointegrations, m_horizon)
        get_predictions({0: result}, m_horizon)

    convert_arrays_to_lists(result)

    return json.dumps({'macro_stats': result})


@app.route('/', methods=['POST'])
def service():
    r = request.values

    bank_ids: list = json.loads(r['bank_ids'])
    m_horizon: int = json.loads(r['m_horizon'])
    h_horizon: int = json.loads(r['h_horizon'])
    scenario: int = json.loads(r['scenario'])
    force_recompute: bool = bool(json.loads(r['force_recompute']))

    calc_date: date = date.fromisoformat(json.loads(r['calc_date']))

    # Get calculation dates range
    dates = get_dates(h_horizon, calc_date)

    # Modeling horizon dates
    m_dates = get_modeling_dates(m_horizon, calc_date)

    # Check if such model already exists
    bank_values = {}
    if not force_recompute:
        for bank_id in bank_ids:
            repay_values = check_if_model_exists(calc_date, bank_id,
                                                 m_horizon, h_horizon,
                                                 scenario, 27)
            risk_values = check_if_model_exists(calc_date, bank_id,
                                                m_horizon, h_horizon,
                                                scenario, 28)
            if repay_values is not None and risk_values is not None:
                if bank_id not in bank_values.keys():
                    bank_values[bank_id] = {}
                bank_values[bank_id]['repay'] = list(
                    map(lambda x: x[0], repay_values))
                bank_values[bank_id]['credit_loss'] = list(
                    map(lambda x: x[0], risk_values))

    new_bank_ids = [bank_id for bank_id in bank_ids if
                    bank_id not in bank_values.keys()]

    # Calc portfolios
    portfolios = get_portfolios(
        new_bank_ids,
        TARGET_FORMULAS,
        dates,
        1
    )
    # Update portfolios dictionary with predictions
    # for each formula
    for _, vals in portfolios.items():
        for formula, val in vals.items():
            _, counts = make_stationary(np.array([val['values']]))
            val['stationary_counts'] = counts[0]

    # Get macro indicators
    icreds_le = get_macro_indicators(
        m_dates,
        'I_CRED_LE',
        scenario
    )
    icreds_p = get_macro_indicators(
        m_dates,
        'I_CRED_P',
        scenario
    )

    macro_list = get_macro_names()

    h_indicators = get_indicator_values(
        dates=dates,
        indicator_names=macro_list,
        scenario_id=scenario
    )

    make_checks_and_correlations(portfolios, h_indicators, macro_list, dates,
                                 m_dates, scenario, get_indicator_values)
    make_predictions(portfolios, dates, m_dates, scenario,
                     m_horizon, get_indicator_values)

    # Calculate RVPS for NPL and PL, repay for PL:
    bank_stats = get_bank_stats(portfolios, m_horizon, icreds_p, icreds_le)

    for bank_id, vals in bank_stats.items():
        ind_names = ['credit_risk_loss', 'credit_repay'] + \
                    list(bank_stats[bank_id]['predictions'].keys())
        values = [bank_stats[bank_id]['credit_loss'],
                  bank_stats[bank_id]['repay']] + \
                 list(bank_stats[bank_id]['predictions'].values())

        save_modeling_values(bank_id, calc_date, m_horizon, h_horizon,
                             scenario, ind_names, values, m_dates)

    bank_stats = {**bank_stats, **bank_values}

    convert_arrays_to_lists(bank_stats)
    # convert_arrays_to_lists(portfolios)

    return json.dumps({'bank_stats': bank_stats,
                       'm_dates': [f'{d.day:02d}.{d.month:02d}.{d.year:04d}' for
                                   d in m_dates]})


@app.route('/get_banks')
def get_banks():
    banks = get_all_banks()
    return json.dumps(banks)


@app.route('/gen_template', methods=['POST'])
def gen_template():
    # should contain dt, indicator names list, and modeling horizon
    params = dict(request.values)

    calc_date: date = date.fromisoformat(json.loads(params['calc_date']))
    m_horizon: int = int(params['modeling_horizon'])

    if 'indicator_names' not in params:
        names = get_macro_names()
    else:
        names = params['indicator_names']

    template_bytes = get_template(calc_date, names, m_horizon)
    template_bytes = base64.b64encode(template_bytes).decode('ascii')

    return template_bytes


@app.route('/parse_data', methods=['POST'])
def parse_data():
    bank_id = int(request.values['bank_id'])
    parse_date = request.values['dt']
    parse_date = date.fromisoformat(json.loads(parse_date))

    parse_to_db(bank_id, parse_date, 101, 13, [0, 10, 11])

    return Response(status=200)
