from src.orders import get_orders
from src.branches import get_branches_and_accounts
from src.login import do_login
from timeit import timeit


def main():
    try:
        session = do_login()
        branches, accounts = get_branches_and_accounts(session)
        orders = get_orders(session, accounts, "05/12/2020", "10/12/2020")
        print("Total branches: %s " % len(branches))
        print("Total accounts: %s " % len(accounts))
        print("Total orders:  %s" % len(orders))
    except Exception as err:
        print(err)


main()
