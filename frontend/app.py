import base64
import datetime
import io
import json
from flask import Flask, request, render_template, send_file, redirect
from matplotlib import ticker
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from requests import post, get

app = Flask(__name__)

scenarios = {
    2: 'Фактический',
    3: 'Негативный',
    4: 'Позитивный'
}


@app.route('/')
def main():
    return render_template('authorization.html')


@app.route('/calc.html')
def calc_page():
    response = get('http://credit-risk-app:5001/get_banks')
    banks = list(response.json())

    return render_template('calc.html', banks=banks)


@app.route('/report.html', methods=['GET', 'POST'])
def get_result():
    if request.method == 'POST':
        day, month, year = list(
            map(int, str(request.form.get('datepicker')).split('-'))
        )
        date = str(datetime.date(year, month, day))
        scenario = int(request.form.get('scenarios'))
        recompute = request.form.get('recompute')

        data = {
            'calc_date': json.dumps(date),
            'm_horizon': int(request.form.get('mh')),
            'h_horizon': int(request.form.get('hh')),
            # 'target': int(request.form.get('target')),
            'scenario': scenario,
            'force_recompute': int(recompute)
        }

        requested_banks = list(map(int, request.form.getlist('banks')))

        data['bank_ids'] = json.dumps(requested_banks)

        response = post('http://credit-risk-app:5001', data=data)
        result = dict(response.json())
        dates = result['m_dates']

        for bank_id, values in result['bank_stats'].items():
            cl = [v / 1000000 for v in values['credit_loss']]
            rp = [v / 1000000 for v in values['repay']]

            values['img_loss'] = get_img(cl, dates)
            values['img_repay'] = get_img(rp, dates)

        result['dt'] = '{d:02d}.{m:02d}.{y:04d}'.format(d=day, m=month, y=year)
        result['scenario'] = scenarios[scenario]
        result['m_horizon'] = data['m_horizon']
    else:
        result = {'dt': "", 'scenario': "", 'm_horizon': "", 'bank_stats': {}}

    return render_template('report.html', result=result)


@app.route('/dataload.html')
def view_dataload():
    response = get('http://credit-risk-app:5001/get_banks')
    banks = list(response.json())

    return render_template('dataload.html', banks=banks)


@app.route('/download_template', methods=['POST'])
def get_xlsx_template():
    m_horizon = request.form.get('m_horizon')
    dt = request.form.get('datetime')
    day, month, year = list(map(int, dt.split('-')))
    dt = datetime.date(year, month, day).isoformat()

    template_b64 = post('http://credit-risk-app:5001/gen_template',
                        data={'calc_date': json.dumps(dt),
                              'modeling_horizon': int(m_horizon)}).text
    template = base64.b64decode(template_b64)

    fp = io.BytesIO(template)

    return send_file(
        fp,
        mimetype='application/vnd.openxmlformats-'
                 'officedocument.spreadsheetml.sheet',
        as_attachment=True,
        attachment_filename='template.xlsx'
    )


@app.route('/parse_data', methods=['POST'])
def parse_data():
    dt = request.form.get('dt')
    day, month, year = list(map(int, dt.split('-')))
    dt = datetime.date(year, month, day).isoformat()
    bank_id = int(request.form.get('bank'))

    post('http://credit-risk-app:5001/parse_data',
         data={'dt': json.dumps(dt),
               'bank_id': bank_id})

    return redirect('/dataload.html', 202)


@app.route('/dataload.html', methods=['POST'])
def get_macro():
    m_horizon = request.form.get('m_horizon')
    dt = request.form.get('datetime')
    d, m, y = dt.split('-')
    dt = f'{y}-{m}-{d}'

    res = post('http://credit-risk-app:5001/macro',
               data={'m_horizon': int(m_horizon),
                     'calc_date': json.dumps(dt)})

    return res.json()['macro_stats']


def get_img(data, x_ticklabels):
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)

    axis.set_xticks(list(range(len(data))))

    @ticker.FuncFormatter
    def formatter(x, _):
        return f'{int(x):,}'.replace(',', ' ')

    axis.yaxis.set_major_formatter(formatter)

    axis.set_xlabel("Горизонт моделирования, кварталы")
    axis.set_ylabel("Объем, млдр.руб")

    axis.set_xticklabels(x_ticklabels)

    axis.grid()
    axis.plot(data)

    # Convert plot to PNG image
    png_image = io.BytesIO()
    FigureCanvas(fig).print_png(png_image)

    # Encode PNG image to base64 string
    b64_img = "data:image/png;base64,"
    b64_img += base64.b64encode(png_image.getvalue()).decode('utf8')

    return b64_img
