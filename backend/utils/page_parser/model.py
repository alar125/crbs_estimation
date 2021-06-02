from datetime import date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, Date

Base = declarative_base()


class Bank(Base):
    __tablename__ = 'bank'
    id = Column(Integer, primary_key=True)
    name = Column(String)


class Form101(Base):
    __tablename__ = 'form_101'

    account = Column(Integer, primary_key=True)
    dt = Column(Date, primary_key=True)
    bank_id = Column(ForeignKey('bank.id'), primary_key=True)
    val_ruble = Column(Integer)
    val_currency = Column(Integer)

    def __init__(self, acc_id: int, rub_credit: int, cur_credit: int,
                 bank_id: int, d: date):
        self.account = acc_id
        self.val_ruble = rub_credit
        self.val_currency = cur_credit
        self.bank_id = bank_id
        self.dt = d

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"Account #{self.account}, Date {self.dt}:" \
               f"Rub: {self.val_ruble},Others: {self.val_currency}," \
               f"Total = {self.val_ruble + self.val_currency}"
