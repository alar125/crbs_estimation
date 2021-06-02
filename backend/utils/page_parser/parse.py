from .model import Form101, Bank
from urllib import request
from bs4 import BeautifulSoup
from datetime import date
from sqlalchemy import and_, create_engine
from sqlalchemy.orm import sessionmaker
from typing import List
from os import getenv


def parse_to_db(bank: int,
                d: date,
                form: int,
                column_count: int,
                target_columns: List[int]) -> None:
    """
    Parse cbr.ru page of a given form, bank and date
    :param bank: bank id to parse page for
    :param d: target date
    :param form: target form id
    :param column_count: number of columns in a given form
    :param target_columns: list of column indices to take
    :return: None
    """
    db_user = getenv('DB_USER')
    db_pass = getenv('DB_PASSWORD')
    db_host = getenv('DB_HOST')
    db_name = getenv('DB_NAME')

    engine = create_engine(
        f'postgresql://{db_user}:{db_pass}@{db_host}/{db_name}')

    s_constructor = sessionmaker()
    session = s_constructor(bind=engine)

    url = f'https://www.cbr.ru/banking_sector/credit/coinfo/f{form}/' \
          f'?regnum={bank}&dt={d.year:02d}-{d.month:02d}-{d.day:02d}'

    response = request.urlopen(url)
    web_content = response.read()
    soup = BeautifulSoup(web_content, "lxml")

    bank_ = session.query(Bank).filter(Bank.id == bank).one_or_none()
    if bank_ is None:
        bank_name = soup.find('div',
                              class_='coinfo_item_text col-md-13 offset-md-1')

        if bank_name is None:
            print('Seems like page does not contain bank information. Skipping')
            return

        session.add(Bank(id=bank, name=bank_name.string))
        # We need to commit here, otherwise we'll get
        # foreign key violation error
        session.commit()

    table_lines = soup.find_all('tr')

    for line in table_lines:
        item = line.contents[0]
        parsed_items = []

        for sibling in item.next_siblings:
            # We only need <td> tags + skip row breaks
            if sibling.string == '\n' or sibling.name != 'td':
                continue
            parsed_items.append(sibling.string)

        # TODO: find a better way to exclude headers
        if len(parsed_items) == column_count \
                and parsed_items != [str(x) for x
                                     in range(1,
                                              column_count + 1)]:
            try:
                sublist = list(map(lambda x: int(''.join(x.split())),
                                   [parsed_items[i] for i in target_columns]))
                account = session.query(Form101). \
                    filter(and_(Form101.account == sublist[0],
                                Form101.bank_id == bank,
                                Form101.dt == d)).one_or_none()
                if account is None:
                    session.add(Form101(*sublist, bank_id=bank, d=d))
            except ValueError:
                pass

    session.commit()
    session.close()
