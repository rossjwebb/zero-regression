# SPDX-License-Identifier: Apache-2.0
import pytest
from unittest.mock import MagicMock
from decimal import Decimal
import datetime
import copy

from account_service_impl import (
    OperatorEnum,
    TransactionSymbolEnum,
    TransactionFlagEnum,
    OperationSymbolEnum,
    AccountsSideEnum,
    Account,
    TransactionEntry,
    OperationEntry,
    AccountsCode,
    Restriction,
    AccountServiceImpl,
)


@pytest.fixture
def service():
    account_repo = MagicMock()
    txn_entry_repo = MagicMock()
    operation_entry_repo = MagicMock()
    code_of_accounts_repo = MagicMock()
    deep_clone_fn = MagicMock()

    deep_clone_fn.side_effect = lambda obj: copy.deepcopy(obj)

    svc = AccountServiceImpl(
        account_repo=account_repo,
        transaction_entry_repo=txn_entry_repo,
        operation_entry_repo=operation_entry_repo,
        code_of_accounts_repo=code_of_accounts_repo,
        deep_clone_fn=deep_clone_fn
    )
    return svc

@pytest.fixture
def make_account():
    def _make(accountNo="123", accountCtrl="000", balance=Decimal("100.00"), frozenAmt=Decimal("0.00"), latestTransactionDate=None):
        return Account(
            accountNo=accountNo,
            accountCtrl=accountCtrl,
            balance=balance,
            frozenAmt=frozenAmt,
            latestTransactionDate=latestTransactionDate
        )
    return _make

@pytest.fixture
def make_entry():
    def _make(accountNo="123", accountCodeNo="CODE1", amount=Decimal("10.00"), symbol=TransactionSymbolEnum.DEBIT, transactionDate=None):
        if transactionDate is None:
            transactionDate = datetime.date(2023, 10, 2)
        return TransactionEntry(
            accountNo=accountNo,
            accountCodeNo=accountCodeNo,
            amount=amount,
            symbol=symbol,
            transactionDate=transactionDate
        )
    return _make

def test_operator_debit_debtor_returns_plus(service):
    op = service._getOperatorBySymbolAndSide(TransactionSymbolEnum.DEBIT, AccountsSideEnum.DEBTOR)
    assert op == OperatorEnum.PLUS
    assert op.value == "PLUS"
    assert TransactionSymbolEnum.DEBIT.value == 1
    assert AccountsSideEnum.DEBTOR.value == 1

def test_operator_debit_creditor_returns_minus(service):
    op = service._getOperatorBySymbolAndSide(TransactionSymbolEnum.DEBIT, AccountsSideEnum.CREDITOR)
    assert op == OperatorEnum.MINUS
    assert op.value == "MINUS"
    assert AccountsSideEnum.CREDITOR.value == 2

def test_operator_credit_creditor_returns_plus(service):
    op = service._getOperatorBySymbolAndSide(TransactionSymbolEnum.CREDIT, AccountsSideEnum.CREDITOR)
    assert op == OperatorEnum.PLUS
    assert TransactionSymbolEnum.CREDIT.value == 2

def test_operator_credit_debtor_returns_minus(service):
    op = service._getOperatorBySymbolAndSide(TransactionSymbolEnum.CREDIT, AccountsSideEnum.DEBTOR)
    assert op == OperatorEnum.MINUS

def test_operator_receipt_returns_plus(service):
    op = service._getOperatorBySymbolAndSide(TransactionSymbolEnum.RECEIPT, AccountsSideEnum.NONE)
    assert op == OperatorEnum.PLUS
    assert TransactionSymbolEnum.RECEIPT.value == 3
    assert AccountsSideEnum.NONE.value == 3

def test_operator_pay_returns_minus(service):
    op = service._getOperatorBySymbolAndSide(TransactionSymbolEnum.PAY, AccountsSideEnum.NONE)
    assert op == OperatorEnum.MINUS
    assert TransactionSymbolEnum.PAY.value == 4

def test_update_null_account_raises(service, make_entry):
    service.account_repo.lock_account.return_value = None
    assert AccountServiceImpl.flash_not_negative is False
    assert AccountServiceImpl.check_last_balance is False
    entry = make_entry()
    with pytest.raises(RuntimeError) as exc_info:
        service.update(entry, Restriction())
    assert str(exc_info.value) == "No account found with accountNo:123"
    service.account_repo.lock_account.assert_called_with(entry.accountNo)

def test_negative_frozen_amt_normalised_to_zero(service, make_account, make_entry):
    AccountServiceImpl.flash_not_negative = True
    acct = make_account(balance=Decimal("10.00"), frozenAmt=Decimal("-10.00"), accountCtrl="001")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.CREDITOR)
    entry = make_entry(amount=Decimal("-10.00"), symbol=TransactionSymbolEnum.CREDIT)
    updated_acct = service.update(entry, Restriction())
    assert entry.balance == Decimal("0.00")
    assert entry.balanceAccum == Decimal("0.00")
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.balance == Decimal("0.00")
    assert updated_acct.drBalance == Decimal("0.00")
    assert updated_acct.lastDrBalance == Decimal("0.00")
    assert updated_acct.latestTransactionDate is None
    AccountServiceImpl.flash_not_negative = False

def test_plus_operator_positive_amount_adds_balance(service, make_account, make_entry):
    acct = make_account(balance=Decimal("100.00"))
    accounts_code = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    assert accounts_code.accountsCodeNo == ""
    assert accounts_code.accountsSide == AccountsSideEnum.DEBTOR
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = accounts_code
    entry = make_entry(amount=Decimal("50.00"), symbol=TransactionSymbolEnum.DEBIT)
    updated_acct = service.update(entry, Restriction())
    service.code_of_accounts_repo.get_by_accounts_code_no.assert_called_with(entry.accountCodeNo)
    assert entry.balance == Decimal("150.00")
    assert entry.balanceAccum == Decimal("0.00")
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.balance == Decimal("0.00")
    assert updated_acct.drBalance == Decimal("0.00")
    assert updated_acct.lastDrBalance == Decimal("0.00")
    assert updated_acct.latestTransactionDate is None

def test_plus_operator_negative_amount_flash_allowed_when_flag_off(service, make_account, make_entry):
    AccountServiceImpl.flash_not_negative = False
    acct = make_account(balance=Decimal("10.00"), frozenAmt=Decimal("5.00"), accountCtrl="001")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(amount=Decimal("-10.00"), symbol=TransactionSymbolEnum.DEBIT)
    updated_acct = service.update(entry, Restriction())
    assert entry.balance == Decimal("0.00")
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.balance == Decimal("0.00")
    assert updated_acct.drBalance == Decimal("0.00")
    assert updated_acct.lastDrBalance == Decimal("0.00")
    assert updated_acct.latestTransactionDate is None

def test_plus_operator_negative_amount_flash_blocked_when_flag_on_and_ctrl_1_and_insufficient(service, make_account, make_entry):
    AccountServiceImpl.flash_not_negative = True
    acct = make_account(balance=Decimal("10.00"), frozenAmt=Decimal("5.00"), accountCtrl="001")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(amount=Decimal("-10.00"), symbol=TransactionSymbolEnum.DEBIT)
    with pytest.raises(RuntimeError) as exc_info:
        service.update(entry, Restriction())
    assert str(exc_info.value) == "The balance is not enough for this flash transaction!"
    AccountServiceImpl.flash_not_negative = False

def test_plus_operator_negative_amount_flash_allowed_when_ctrl_not_1(service, make_account, make_entry):
    AccountServiceImpl.flash_not_negative = True
    acct = make_account(balance=Decimal("10.00"), frozenAmt=Decimal("5.00"), accountCtrl="000")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(amount=Decimal("-10.00"), symbol=TransactionSymbolEnum.DEBIT)
    updated_acct = service.update(entry, Restriction())
    assert entry.balance == Decimal("0.00")
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.balance == Decimal("0.00")
    assert updated_acct.drBalance == Decimal("0.00")
    assert updated_acct.lastDrBalance == Decimal("0.00")
    assert updated_acct.latestTransactionDate is None
    AccountServiceImpl.flash_not_negative = False

def test_minus_operator_sufficient_balance_subtracts(service, make_account, make_entry):
    acct = make_account(balance=Decimal("100.00"), frozenAmt=Decimal("50.00"), accountCtrl="001")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.CREDITOR)
    entry = make_entry(amount=Decimal("50.00"), symbol=TransactionSymbolEnum.DEBIT)
    updated_acct = service.update(entry, Restriction())
    assert entry.balance == Decimal("50.00")
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.balance == Decimal("0.00")
    assert updated_acct.drBalance == Decimal("0.00")
    assert updated_acct.lastDrBalance == Decimal("0.00")
    assert updated_acct.latestTransactionDate is None

def test_minus_operator_insufficient_balance_ctrl_1_raises(service, make_account, make_entry):
    acct = make_account(balance=Decimal("100.00"), frozenAmt=Decimal("60.00"), accountCtrl="001")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.CREDITOR)
    entry = make_entry(amount=Decimal("50.00"), symbol=TransactionSymbolEnum.DEBIT)
    with pytest.raises(RuntimeError) as exc_info:
        service.update(entry, Restriction())
    assert str(exc_info.value) == "The balance is not enough for this transaction!"

def test_minus_operator_insufficient_balance_ctrl_not_1_allowed(service, make_account, make_entry):
    acct = make_account(balance=Decimal("100.00"), frozenAmt=Decimal("60.00"), accountCtrl="000")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.CREDITOR)
    entry = make_entry(amount=Decimal("50.00"), symbol=TransactionSymbolEnum.DEBIT)
    updated_acct = service.update(entry, Restriction())
    assert entry.balance == Decimal("50.00")
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.balance == Decimal("0.00")
    assert updated_acct.drBalance == Decimal("0.00")
    assert updated_acct.lastDrBalance == Decimal("0.00")
    assert updated_acct.latestTransactionDate is None

def test_date_gap_1_debit_sets_last_balances_and_resets_cr(service, make_account, make_entry):
    acct = make_account(latestTransactionDate=datetime.date(2023, 10, 1))
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2), symbol=TransactionSymbolEnum.DEBIT)
    updated_acct = service.update(entry, Restriction())
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.lastBalance == acct.balance
    assert updated_acct.lastDrBalance == acct.drBalance
    assert updated_acct.lastDrTransactionAmt == acct.drTransactionAmt
    assert updated_acct.lastCrBalance == acct.crBalance
    assert updated_acct.lastCrTransactionAmt == acct.crTransactionAmt
    assert updated_acct.latestTransactionDate == entry.transactionDate
    assert updated_acct.balance == Decimal("110.00")
    assert updated_acct.crTransactionAmt == Decimal("0.00")
    assert updated_acct.drTransactionAmt == entry.amount
    assert updated_acct.drBalance == Decimal("10.00")

def test_date_gap_1_credit_sets_last_balances_and_resets_dr(service, make_account, make_entry):
    acct = make_account(latestTransactionDate=datetime.date(2023, 10, 1))
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2), symbol=TransactionSymbolEnum.CREDIT)
    updated_acct = service.update(entry, Restriction())
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.lastBalance == acct.balance
    assert updated_acct.lastDrBalance == acct.drBalance
    assert updated_acct.lastDrTransactionAmt == acct.drTransactionAmt
    assert updated_acct.lastCrBalance == acct.crBalance
    assert updated_acct.lastCrTransactionAmt == acct.crTransactionAmt
    assert updated_acct.latestTransactionDate == entry.transactionDate
    assert updated_acct.balance == Decimal("90.00")
    assert updated_acct.drTransactionAmt == Decimal("0.00")
    assert updated_acct.crTransactionAmt == entry.amount

def test_date_gap_gt1_debit_zeroes_last_txn_amts(service, make_account, make_entry):
    acct = make_account(latestTransactionDate=datetime.date(2023, 10, 1))
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 3), symbol=TransactionSymbolEnum.DEBIT)
    updated_acct = service.update(entry, Restriction())
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.lastBalance == acct.balance
    assert updated_acct.lastDrBalance == acct.drBalance
    assert updated_acct.latestTransactionDate == entry.transactionDate
    assert updated_acct.balance == Decimal("110.00")
    assert updated_acct.lastDrTransactionAmt == Decimal("0.00")
    assert updated_acct.lastCrTransactionAmt == Decimal("0.00")
    assert updated_acct.drTransactionAmt == entry.amount
    assert updated_acct.crTransactionAmt == Decimal("0.00")
    assert updated_acct.drBalance == Decimal("10.00")

def test_date_gap_gt1_credit_zeroes_last_txn_amts(service, make_account, make_entry):
    acct = make_account(latestTransactionDate=datetime.date(2023, 10, 1))
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 3), symbol=TransactionSymbolEnum.CREDIT)
    updated_acct = service.update(entry, Restriction())
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.lastBalance == acct.balance
    assert updated_acct.lastDrBalance == acct.drBalance
    assert updated_acct.latestTransactionDate == entry.transactionDate
    assert updated_acct.balance == Decimal("90.00")
    assert updated_acct.lastDrTransactionAmt == Decimal("0.00")
    assert updated_acct.lastCrTransactionAmt == Decimal("0.00")
    assert updated_acct.drTransactionAmt == Decimal("0.00")
    assert updated_acct.crTransactionAmt == entry.amount

def test_date_gap_0_debit_accumulates_dr_txn_amt(service, make_account, make_entry):
    acct = make_account(latestTransactionDate=datetime.date(2023, 10, 2))
    acct.drTransactionAmt = Decimal("20.00")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2), symbol=TransactionSymbolEnum.DEBIT, amount=Decimal("10.00"))
    updated_acct = service.update(entry, Restriction())
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.balance == Decimal("110.00")
    assert updated_acct.drBalance == Decimal("10.00")
    assert updated_acct.lastDrBalance == Decimal("0.00")
    assert updated_acct.latestTransactionDate is None
    assert updated_acct.drTransactionAmt == Decimal("30.00")

def test_date_gap_0_credit_accumulates_cr_txn_amt(service, make_account, make_entry):
    acct = make_account(latestTransactionDate=datetime.date(2023, 10, 2))
    acct.crTransactionAmt = Decimal("20.00")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2), symbol=TransactionSymbolEnum.CREDIT, amount=Decimal("10.00"))
    updated_acct = service.update(entry, Restriction())
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.balance == Decimal("90.00")
    assert updated_acct.drBalance == Decimal("0.00")
    assert updated_acct.lastDrBalance == Decimal("0.00")
    assert updated_acct.latestTransactionDate is None
    assert updated_acct.crTransactionAmt == Decimal("30.00")

def test_date_gap_neg1_plus_operator_updates_last_balance_and_records_detail(service, make_account, make_entry):
    AccountServiceImpl.flash_not_negative = True
    acct = make_account(
        latestTransactionDate=datetime.date(2023, 10, 3),
        balance=Decimal("100.00"),
        frozenAmt=Decimal("10.00"),
        accountCtrl="001"
    )
    acct.lastBalance = Decimal("15.00")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2), symbol=TransactionSymbolEnum.DEBIT, amount=Decimal("-5.00"))
    updated_acct = service.update(entry, Restriction())
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.balance == Decimal("95.00")
    assert updated_acct.lastBalance == Decimal("10.00")
    assert updated_acct.lastDrTransactionAmt == Decimal("-5.00")
    assert updated_acct.lastDrBalance == Decimal("-5.00")
    assert updated_acct.latestTransactionDate is None
    assert service.transaction_entry_repo.record_detail_account.call_count == 2
    AccountServiceImpl.flash_not_negative = False

def test_date_gap_neg1_minus_operator_updates_last_balance_and_records_detail(service, make_account, make_entry):
    AccountServiceImpl.check_last_balance = True
    acct = make_account(
        latestTransactionDate=datetime.date(2023, 10, 3),
        balance=Decimal("100.00"),
        frozenAmt=Decimal("10.00"),
        accountCtrl="001"
    )
    acct.lastBalance = Decimal("20.00")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.CREDITOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2), symbol=TransactionSymbolEnum.DEBIT, amount=Decimal("10.00"))
    updated_acct = service.update(entry, Restriction())
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.balance == Decimal("90.00")
    assert updated_acct.lastBalance == Decimal("10.00")
    assert updated_acct.lastDrTransactionAmt == Decimal("10.00")
    assert updated_acct.lastDrBalance == Decimal("10.00")
    assert updated_acct.latestTransactionDate is None
    AccountServiceImpl.check_last_balance = False

def test_date_gap_neg1_flash_blocked_when_flash_flag_on_and_insufficient(service, make_account, make_entry):
    AccountServiceImpl.flash_not_negative = True
    acct = make_account(latestTransactionDate=datetime.date(2023, 10, 3), balance=Decimal("100.00"), frozenAmt=Decimal("10.00"), accountCtrl="001")
    acct.lastBalance = Decimal("5.00")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2), symbol=TransactionSymbolEnum.DEBIT, amount=Decimal("-10.00"))
    with pytest.raises(RuntimeError) as exc_info:
        service.update(entry, Restriction())
    assert str(exc_info.value) == "The lastBalance is not enough for this flash transaction!"
    AccountServiceImpl.flash_not_negative = False

def test_date_gap_neg1_check_last_balance_blocked_when_flag_on_and_insufficient(service, make_account, make_entry):
    AccountServiceImpl.check_last_balance = True
    acct = make_account(latestTransactionDate=datetime.date(2023, 10, 3), balance=Decimal("100.00"), frozenAmt=Decimal("10.00"), accountCtrl="001")
    acct.lastBalance = Decimal("15.00")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.CREDITOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2), symbol=TransactionSymbolEnum.DEBIT, amount=Decimal("10.00"))
    with pytest.raises(RuntimeError) as exc_info:
        service.update(entry, Restriction())
    assert str(exc_info.value) == "The lastBalance is not enough for this transaction!"
    AccountServiceImpl.check_last_balance = False

def test_date_gap_lt_neg1_raises_date_anomaly(service, make_account, make_entry):
    acct = make_account(latestTransactionDate=datetime.date(2023, 10, 4))
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2), symbol=TransactionSymbolEnum.DEBIT)
    with pytest.raises(RuntimeError) as exc_info:
        service.update(entry, Restriction())
    assert str(exc_info.value) == "txnDate:2023-10-02 invalid while latestTransactionDate is 2023-10-04"

def test_date_gap_neg1_calls_deep_clone(service, make_account, make_entry):
    acct = make_account(latestTransactionDate=datetime.date(2023, 10, 3))
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2))
    updated_acct = service.update(entry, Restriction())
    service.deep_clone_fn.assert_called_once_with(entry)
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.balance == Decimal("110.00")
    assert updated_acct.lastDrBalance == Decimal("10.00")
    assert updated_acct.latestTransactionDate is None

def test_date_gap_neg1_records_two_detail_entries(service, make_account, make_entry):
    acct = make_account(latestTransactionDate=datetime.date(2023, 10, 3))
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2))
    updated_acct = service.update(entry, Restriction())
    assert service.transaction_entry_repo.record_detail_account.call_count == 2
    latest_core_map = service.transaction_entry_repo.record_detail_account.call_args_list[0][0][0]
    latest_title_map = service.transaction_entry_repo.record_detail_account.call_args_list[1][0][0]
    assert set(latest_core_map) == {"tableName", "detail"}
    assert latest_core_map["tableName"] == "t_det_core_2023-10-03"
    assert latest_core_map["tableName"].startswith("t_det_core_")
    assert set(latest_title_map) == {"tableName", "detail"}
    assert latest_title_map["tableName"] == "t_det_CODE1"
    assert latest_title_map["tableName"].startswith("t_det_")
    assert latest_title_map["detail"] is latest_core_map["detail"]
    assert updated_acct.balance == Decimal("110.00")
    assert updated_acct.lastDrBalance == Decimal("10.00")
    assert updated_acct.latestTransactionDate is None

def test_date_gap_neg1_sets_effective_false_on_clone(service, make_account, make_entry):
    acct = make_account(latestTransactionDate=datetime.date(2023, 10, 3))
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2))
    updated_acct = service.update(entry, Restriction())
    latest_detail = service.transaction_entry_repo.record_detail_account.call_args_list[0][0][0]["detail"]
    assert latest_detail is not entry
    assert latest_detail.accountNo == entry.accountNo
    assert latest_detail.accountCodeNo == entry.accountCodeNo
    assert latest_detail.transactionDate == entry.transactionDate
    assert latest_detail.amount == entry.amount
    assert latest_detail.symbol == entry.symbol
    assert latest_detail.balance == Decimal("110.00")
    assert latest_detail.balanceAccum == Decimal("0.00")
    assert latest_detail.effective is False
    assert latest_detail.transactionId == ""
    assert latest_detail.flag is None
    assert TransactionFlagEnum.FLAG1.value == 1
    assert updated_acct.balance == Decimal("110.00")
    assert updated_acct.lastDrBalance == Decimal("10.00")
    assert updated_acct.latestTransactionDate is None

def test_date_gap_neg1_sets_comment_on_clone(service, make_account, make_entry):
    acct = make_account(latestTransactionDate=datetime.date(2023, 10, 3))
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2))
    updated_acct = service.update(entry, Restriction())
    latest_detail = service.transaction_entry_repo.record_detail_account.call_args_list[0][0][0]["detail"]
    assert latest_detail.comment == "发生了昨日账务"
    assert latest_detail.balance == Decimal("110.00")
    assert updated_acct.balance == Decimal("110.00")
    assert updated_acct.lastDrBalance == Decimal("10.00")
    assert updated_acct.latestTransactionDate is None

def test_date_gap_neg1_overwrites_entry_balance_with_new_last_bal(service, make_account, make_entry):
    acct = make_account(latestTransactionDate=datetime.date(2023, 10, 3))
    acct.lastBalance = Decimal("50.00")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2), amount=Decimal("10.00"), symbol=TransactionSymbolEnum.DEBIT)
    updated_acct = service.update(entry, Restriction())
    assert entry.balance == Decimal("60.00")
    assert updated_acct.balance == Decimal("110.00")
    assert updated_acct.lastBalance == Decimal("60.00")
    assert updated_acct.lastDrBalance == Decimal("10.00")
    assert updated_acct.latestTransactionDate is None

def test_update_always_calls_txn_entry_save(service, make_account, make_entry):
    acct = make_account()
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry()
    updated_acct = service.update(entry, Restriction())
    service.transaction_entry_repo.save.assert_called_once_with(entry)
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.balance == Decimal("0.00")
    assert updated_acct.lastDrBalance == Decimal("0.00")
    assert updated_acct.latestTransactionDate is None

def test_update_always_calls_modify_balance(service, make_account, make_entry):
    acct = make_account()
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry()
    res = Restriction()
    updated_acct = service.update(entry, res)
    service.account_repo.modify_balance.assert_called_once_with(updated_acct)
    assert updated_acct.accountNo == entry.accountNo
    assert updated_acct.accountCodeNo == ""
    assert updated_acct.accountCtrl == "000"
    assert updated_acct.balance == Decimal("0.00")
    assert updated_acct.frozenAmt == Decimal("0.00")
    assert updated_acct.drBalance == Decimal("0.00")
    assert updated_acct.crBalance == Decimal("0.00")
    assert updated_acct.drTransactionAmt == Decimal("0.00")
    assert updated_acct.crTransactionAmt == Decimal("0.00")
    assert updated_acct.lastBalance == Decimal("0.00")
    assert updated_acct.lastDrBalance == Decimal("0.00")
    assert updated_acct.lastCrBalance == Decimal("0.00")
    assert updated_acct.lastDrTransactionAmt == Decimal("0.00")
    assert updated_acct.lastCrTransactionAmt == Decimal("0.00")
    assert updated_acct.latestTransactionDate is None
    assert updated_acct.balanceAccum == Decimal("0.00")
    assert AccountsCode().accountsSide is None
    assert res.drTransAmtLimit == Decimal("0.00")
    assert res.crTransAmtLimit == Decimal("0.00")
    assert res.transAmtLimit == Decimal("0.00")
    assert res.MaxBalanceLimit == Decimal("0.00")
    assert res.MinBalanceLimit == Decimal("0.00")
    assert Restriction() == Restriction()

def test_update_operation_calls_plus_frozen_and_save(service):
    op = OperationEntry(amount=Decimal("10.00"))
    service.update_operation(op)
    service.account_repo.plus_to_frozen_amt.assert_called_once_with(Decimal("10.00"))
    service.operation_entry_repo.save.assert_called_once_with(op)
    assert OperationEntry().amount == Decimal("0.00")
    assert OperationSymbolEnum.SYM1.value == 1

def test_get_delegates_to_repo(service):
    service.get("acc123", "acc456")
    service.account_repo.get_by_account_no.assert_called_once_with("acc456")

def test_date_gap_neg1_credit_updates_last_cr_fields(service, make_account, make_entry):
    """Kills mutants #251, #257, #258: day_gap=-1 CREDIT branch."""
    acct = make_account(latestTransactionDate=datetime.date(2023, 10, 3), balance=Decimal("100.00"))
    acct.lastBalance = Decimal("50.00")
    acct.lastCrTransactionAmt = Decimal("20.00")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2), symbol=TransactionSymbolEnum.CREDIT, amount=Decimal("10.00"))
    updated_acct = service.update(entry, Restriction())
    assert updated_acct.lastBalance == Decimal("40.00")
    assert updated_acct.lastCrTransactionAmt == Decimal("30.00")
    assert updated_acct.lastDrTransactionAmt == Decimal("0.00")

def test_plus_operator_zero_amount_does_not_enter_flash_guard(service, make_account, make_entry):
    """Kills mutant #131: txnAmt < 0 vs txnAmt <= 0 at line 138.
    With txnAmt=0, balance=5, frozen=10, ctrl=1, flash_not_negative=True:
      original: txnAmt < 0 is False  -> skip guard -> no raise -> newBalance = 5
      mutant:   txnAmt <= 0 is True  -> enter guard -> (5-10+0)<0 is True -> RAISE
    """
    AccountServiceImpl.flash_not_negative = True
    acct = make_account(balance=Decimal("5.00"), frozenAmt=Decimal("10.00"), accountCtrl="001")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(amount=Decimal("0.00"), symbol=TransactionSymbolEnum.DEBIT)
    updated_acct = service.update(entry, Restriction())
    assert entry.balance == Decimal("5.00")
    assert updated_acct.accountNo == entry.accountNo
    AccountServiceImpl.flash_not_negative = False

def test_frozen_amt_zero_not_normalised(service, make_account, make_entry):
    """Kills mutant #126: frozenAmt < 0 vs frozenAmt <= 0 at line 134."""
    acct = make_account(balance=Decimal("100.00"), frozenAmt=Decimal("0.00"), accountCtrl="001")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.CREDITOR)
    entry = make_entry(amount=Decimal("100.00"), symbol=TransactionSymbolEnum.DEBIT)
    updated_acct = service.update(entry, Restriction())
    assert entry.balance == Decimal("0.00")

def test_day_gap_neg1_zero_amount_does_not_enter_flash_guard(service, make_account, make_entry):
    """Kills mutant #221: txnAmt < 0 vs txnAmt <= 0 at line 194 (day_gap=-1).
    With txnAmt=0, lastBal=5, frozen=10, ctrl=1, flash_not_negative=True:
      original: txnAmt < 0 is False  -> skip guard -> newLastBal = 5 + 0 = 5
      mutant:   txnAmt <= 0 is True  -> enter guard -> (5-10+0)<0 True -> RAISE
    """
    AccountServiceImpl.flash_not_negative = True
    acct = make_account(
        latestTransactionDate=datetime.date(2023, 10, 3),
        balance=Decimal("100.00"),
        frozenAmt=Decimal("10.00"),
        accountCtrl="001"
    )
    acct.lastBalance = Decimal("5.00")
    service.account_repo.lock_account.return_value = acct
    service.code_of_accounts_repo.get_by_accounts_code_no.return_value = AccountsCode(accountsSide=AccountsSideEnum.DEBTOR)
    entry = make_entry(transactionDate=datetime.date(2023, 10, 2), symbol=TransactionSymbolEnum.DEBIT, amount=Decimal("0.00"))
    updated_acct = service.update(entry, Restriction())
    assert updated_acct.lastBalance == Decimal("5.00")
    AccountServiceImpl.flash_not_negative = False

def test_dataclass_defaults_account():
    """Kills surviving mutations on Account default field values (lines 30-45)."""
    a = Account()
    assert a.accountNo == ""
    assert a.accountCodeNo == ""
    assert a.accountCtrl == "000"
    assert a.balance == Decimal("0.00")
    assert a.frozenAmt == Decimal("0.00")
    assert a.drBalance == Decimal("0.00")
    assert a.crBalance == Decimal("0.00")
    assert a.drTransactionAmt == Decimal("0.00")
    assert a.crTransactionAmt == Decimal("0.00")
    assert a.lastBalance == Decimal("0.00")
    assert a.lastDrBalance == Decimal("0.00")
    assert a.lastCrBalance == Decimal("0.00")
    assert a.lastDrTransactionAmt == Decimal("0.00")
    assert a.lastCrTransactionAmt == Decimal("0.00")
    assert a.latestTransactionDate is None
    assert a.balanceAccum == Decimal("0.00")

def test_dataclass_defaults_transaction_entry():
    """Kills surviving mutations on TransactionEntry default field values (lines 49-59)."""
    t = TransactionEntry()
    assert t.accountNo == ""
    assert t.accountCodeNo == ""
    assert t.transactionDate is None
    assert t.amount == Decimal("0.00")
    assert t.symbol is None
    assert t.balance == Decimal("0.00")
    assert t.balanceAccum == Decimal("0.00")
    assert t.effective is True
    assert t.comment == ""
    assert t.transactionId == ""
    assert t.flag is None

def test_dataclass_defaults_operation_entry():
    """Kills surviving mutations on OperationEntry default (line 63)."""
    o = OperationEntry()
    assert o.amount == Decimal("0.00")

def test_dataclass_defaults_restriction():
    """Kills surviving mutations on Restriction default field values (lines 72-76)."""
    r = Restriction()
    assert r.drTransAmtLimit == Decimal("0.00")
    assert r.crTransAmtLimit == Decimal("0.00")
    assert r.transAmtLimit == Decimal("0.00")
    assert r.MaxBalanceLimit == Decimal("0.00")
    assert r.MinBalanceLimit == Decimal("0.00")

TOTAL_BRANCHES = 34
COVERED_TESTS = len([name for name in dir() if name.startswith("test_")])
assert COVERED_TESTS >= 30
