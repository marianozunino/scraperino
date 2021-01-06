from datetime import datetime, timedelta
from src.branches import get_branches_and_accounts
from src.login import do_login
from src.payments import Payments


def main():
    try:
        session = do_login()
        branches, accounts = get_branches_and_accounts(session)
        # orders = get_orders(session, accounts, "05/12/2020", "10/12/2020")
        Payments(
            session,
            accounts,
            datetime.today() - timedelta(days=9),
            datetime.today() + timedelta(days=20),
        )
    # print("Total branches: %s " % len(branches))
    # print("Total accounts: %s " % len(accounts))
    # print("Total orders:  %s" % len(orders))
    # with open("orders.json", "w") as fp:
    #     json.dump(orders, fp, indent=4)
    except Exception as err:
        print(err)


main()
