from dataclasses import dataclass
from decimal import Decimal
import datetime
from enum import Enum
from typing import Optional


class OperatorEnum(Enum):
    PLUS = "PLUS"
    MINUS = "MINUS"

class TransactionSymbolEnum(Enum):
    DEBIT = 1
    CREDIT = 2
    RECEIPT = 3
    PAY = 4

class AccountsSideEnum(Enum):
    DEBTOR = 1
    CREDITOR = 2
    NONE = 3

class TransactionFlagEnum(Enum):
    FLAG1 = 1

class OperationSymbolEnum(Enum):
    SYM1 = 1

@dataclass
class Account:
    accountNo: str = ""
    accountCodeNo: str = ""
    accountCtrl: str = "000"
    balance: Decimal = Decimal("0.00")
    frozenAmt: Decimal = Decimal("0.00")
    drBalance: Decimal = Decimal("0.00")
    crBalance: Decimal = Decimal("0.00")
    drTransactionAmt: Decimal = Decimal("0.00")
    crTransactionAmt: Decimal = Decimal("0.00")
    lastBalance: Decimal = Decimal("0.00")
    lastDrBalance: Decimal = Decimal("0.00")
    lastCrBalance: Decimal = Decimal("0.00")
    lastDrTransactionAmt: Decimal = Decimal("0.00")
    lastCrTransactionAmt: Decimal = Decimal("0.00")
    latestTransactionDate: Optional[datetime.date] = None
    balanceAccum: Decimal = Decimal("0.00")

@dataclass
class TransactionEntry:
    accountNo: str = ""
    accountCodeNo: str = ""
    transactionDate: Optional[datetime.date] = None
    amount: Decimal = Decimal("0.00")
    symbol: Optional[TransactionSymbolEnum] = None
    balance: Decimal = Decimal("0.00")
    balanceAccum: Decimal = Decimal("0.00")
    effective: bool = True
    comment: str = ""
    transactionId: str = ""
    flag: Optional[TransactionFlagEnum] = None

@dataclass
class OperationEntry:
    amount: Decimal = Decimal("0.00")

@dataclass
class AccountsCode:
    accountsCodeNo: str = ""
    accountsSide: Optional[AccountsSideEnum] = None

@dataclass
class Restriction:
    drTransAmtLimit: Decimal = Decimal("0.00")
    crTransAmtLimit: Decimal = Decimal("0.00")
    transAmtLimit: Decimal = Decimal("0.00")
    MaxBalanceLimit: Decimal = Decimal("0.00")
    MinBalanceLimit: Decimal = Decimal("0.00")

class AccountServiceImpl:
    flash_not_negative = False
    check_last_balance = False

    def __init__(self, account_repo, transaction_entry_repo, operation_entry_repo, code_of_accounts_repo, deep_clone_fn):
        self.account_repo = account_repo
        self.transaction_entry_repo = transaction_entry_repo
        self.operation_entry_repo = operation_entry_repo
        self.code_of_accounts_repo = code_of_accounts_repo
        self.deep_clone_fn = deep_clone_fn

    def get(self, accountsNo: str, accountNo: str) -> Account:
        return self.account_repo.get_by_account_no(accountNo)

    def _getOperatorBySymbolAndSide(self, symbol: TransactionSymbolEnum, side: AccountsSideEnum) -> OperatorEnum:
        if symbol == TransactionSymbolEnum.DEBIT:
            if side == AccountsSideEnum.DEBTOR:
                return OperatorEnum.PLUS
            else:
                return OperatorEnum.MINUS
        elif symbol == TransactionSymbolEnum.CREDIT:
            if side == AccountsSideEnum.CREDITOR:
                return OperatorEnum.PLUS
            else:
                return OperatorEnum.MINUS
        elif symbol == TransactionSymbolEnum.RECEIPT:
            return OperatorEnum.PLUS
        else:
            return OperatorEnum.MINUS

    def update_operation(self, entry: OperationEntry) -> None:
        self.account_repo.plus_to_frozen_amt(entry.amount)
        self.operation_entry_repo.save(entry)
        return None

    def update(self, entry: TransactionEntry, res: Restriction) -> Account:
        txnDate = entry.transactionDate
        currentAccount = self.account_repo.lock_account(entry.accountNo)

        if currentAccount is None:
            raise RuntimeError("No account found with accountNo:" + entry.accountNo)

        balance = currentAccount.balance
        frozenAmt = currentAccount.frozenAmt
        newBalance = Decimal("0.00")
        latestTxnDate = currentAccount.latestTransactionDate
        txnAmt = entry.amount
        drTxnAmt = currentAccount.drTransactionAmt
        crTxnAmt = currentAccount.crTransactionAmt
        drBalance = currentAccount.drBalance
        crBalance = currentAccount.crBalance
        entry.balanceAccum = Decimal("0.00")

        accounts_code = self.code_of_accounts_repo.get_by_accounts_code_no(entry.accountCodeNo)
        operator = self._getOperatorBySymbolAndSide(entry.symbol, accounts_code.accountsSide)

        if frozenAmt < Decimal("0.00"):
            frozenAmt = Decimal("0.00")

        if operator == OperatorEnum.PLUS:
            if txnAmt < Decimal("0.00"):
                if self.flash_not_negative and (balance - frozenAmt + txnAmt) < Decimal("0.00") and len(currentAccount.accountCtrl) >= 3 and currentAccount.accountCtrl[2] == "1":
                    raise RuntimeError("The balance is not enough for this flash transaction!")
            newBalance = balance + txnAmt
        elif operator == OperatorEnum.MINUS:
            if (balance - frozenAmt - txnAmt) < Decimal("0.00") and len(currentAccount.accountCtrl) >= 3 and currentAccount.accountCtrl[2] == "1":
                raise RuntimeError("The balance is not enough for this transaction!")
            newBalance = balance - txnAmt

        entry.balance = newBalance
        account = Account()
        account.accountNo = entry.accountNo

        if latestTxnDate is not None:
            day_gap = (txnDate - latestTxnDate).days
            if day_gap == 1:
                account.lastBalance = balance
                account.lastDrBalance = drBalance
                account.lastDrTransactionAmt = drTxnAmt
                account.lastCrBalance = crBalance
                account.lastCrTransactionAmt = crTxnAmt
                account.latestTransactionDate = txnDate
                account.balance = newBalance
                if entry.symbol == TransactionSymbolEnum.DEBIT:
                    account.drTransactionAmt = txnAmt
                    account.crTransactionAmt = Decimal("0.00")
                    account.drBalance = currentAccount.drBalance + txnAmt
                else:
                    account.drTransactionAmt = Decimal("0.00")
                    account.crTransactionAmt = txnAmt
            elif day_gap > 1:
                account.lastBalance = balance
                account.lastDrBalance = drBalance
                account.lastDrTransactionAmt = Decimal("0.00")
                account.lastCrTransactionAmt = Decimal("0.00")
                account.latestTransactionDate = txnDate
                account.balance = newBalance
                if entry.symbol == TransactionSymbolEnum.DEBIT:
                    account.drTransactionAmt = txnAmt
                    account.crTransactionAmt = Decimal("0.00")
                    account.drBalance = currentAccount.drBalance + txnAmt
                else:
                    account.drTransactionAmt = Decimal("0.00")
                    account.crTransactionAmt = txnAmt
            elif day_gap == 0:
                account.balance = newBalance
                if entry.symbol == TransactionSymbolEnum.DEBIT:
                    account.drTransactionAmt = drTxnAmt + txnAmt
                    account.drBalance = currentAccount.drBalance + txnAmt
                else:
                    account.crTransactionAmt = crTxnAmt + txnAmt
            elif day_gap == -1:
                account.balance = newBalance
                newLastBal = Decimal("0.00")
                lastBal = currentAccount.lastBalance
                if operator == OperatorEnum.PLUS:
                    if txnAmt < Decimal("0.00"):
                        if self.flash_not_negative and len(currentAccount.accountCtrl) >= 3 and currentAccount.accountCtrl[2] == "1" and (lastBal - frozenAmt + txnAmt) < Decimal("0.00"):
                            raise RuntimeError("The lastBalance is not enough for this flash transaction!")
                    newLastBal = lastBal + txnAmt
                else:
                    if self.check_last_balance and len(currentAccount.accountCtrl) >= 3 and currentAccount.accountCtrl[2] == "1" and (lastBal - frozenAmt - txnAmt) < Decimal("0.00"):
                        raise RuntimeError("The lastBalance is not enough for this transaction!")
                    newLastBal = lastBal - txnAmt

                account.lastBalance = newLastBal
                lastDrTxnAmt = currentAccount.lastDrTransactionAmt
                lastCrTxnAmt = currentAccount.lastCrTransactionAmt
                if entry.symbol == TransactionSymbolEnum.DEBIT:
                    account.lastDrTransactionAmt = lastDrTxnAmt + txnAmt
                    account.lastDrBalance = currentAccount.lastDrBalance + txnAmt
                else:
                    account.lastCrTransactionAmt = lastCrTxnAmt + txnAmt

                latestDetail = self.deep_clone_fn(entry)
                latestDetail.effective = False
                latestDetail.comment = "发生了昨日账务"
                latestCoreMap = {
                    "tableName": "t_det_core_" + str(latestTxnDate),
                    "detail": latestDetail
                }
                self.transaction_entry_repo.record_detail_account(latestCoreMap)
                latestAcctTitleMap = {
                    "tableName": "t_det_" + latestDetail.accountCodeNo,
                    "detail": latestDetail
                }
                self.transaction_entry_repo.record_detail_account(latestAcctTitleMap)
                entry.balance = newLastBal
            else:
                raise RuntimeError("txnDate:" + str(txnDate) + " invalid while latestTransactionDate is " + str(latestTxnDate))

        self.transaction_entry_repo.save(entry)
        self.account_repo.modify_balance(account)
        return account
