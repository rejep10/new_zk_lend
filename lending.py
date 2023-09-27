import asyncio
import random
from abi_eth import ABI_ETH,eth_address
from zk_lend_abi import zk_market_address,zk_eth_address,ZK_LEND_ABI
from loguru import logger
from starknet_py.contract import Contract
from starknet_py.net.account.account import Account
from starknet_py.net.gateway_client import GatewayClient
from starknet_py.net.models import StarknetChainId
from starknet_py.net.signer.stark_curve_signer import KeyPair

delay = (1,10)

amount_zk = random.uniform(0.0002,0.0002)

scan = 'https://starkscan.co/tx/'

enable_deposite = False
enable_withdraw = True
async def deposite(key,address):
    try:
        account = Account(address=address,
                          client=GatewayClient(net='mainnet'),
                          key_pair=KeyPair.from_private_key(int(key[2:], 16)),
                          chain=StarknetChainId.MAINNET)
        global amount_zk
        amount = amount_zk
        current_nonce = await account.get_nonce()
        eth_balance_wei = await account.get_balance()
        eth_balance = eth_balance_wei / 10 ** 18  # текущий баланс в эфирах

        if amount > eth_balance:  # проверка баланса
            logger.info(
                f'Случайное количество эфиров ({amount}) больше текущего баланса ({eth_balance}). Пропускаем кошелек.')
            return  # выход из функции, не выполняя свап

        amount_wei = int(amount * 10 ** 18)  # перевод в wei
        logger.info(f'Starts to deposit to zkLend {amount} of ETH')


        approve = Contract(
            address=eth_address,
            abi=ABI_ETH,
            provider=account,
        )
        deposit = Contract(
            address=zk_market_address,
            abi=ZK_LEND_ABI,
            provider=account,
        )
        approve_tx = approve.functions["approve"].prepare(
            zk_market_address,
            amount_wei
        )

        deposit_tx = deposit.functions["deposit"].prepare(
            eth_address,
            amount_wei
        )

        calls = [approve_tx, deposit_tx]
        tx = await account.execute(calls=calls, auto_estimate=True,cairo_version=1,nonce=current_nonce)
        status = await account.client.wait_for_tx(tx.transaction_hash)
        if status.status.name in ['SUCCEEDED', 'ACCEPTED_ON_L1', 'ACCEPTED_ON_L2']:
            current_nonce += 1
            logger.success(
                f'{address} - транзакция подтвердилась, аккаунт успешно отправил ETH {scan}{hex(tx.transaction_hash)}')
            return 'updated'
        else:
            logger.error(f'{address} - транзакция неуспешна...')
            return 'error in tx'
    except Exception as e:
        error = str(e)
        if 'StarknetErrorCode.INSUFFICIENT_ACCOUNT_BALANCE' in error:
            logger.error(f'{address} - Не хватает баланса на деплой аккаунта...')
            return 'not balance'
        else:
            logger.error(f'{address} - ошибка {e}')
        return e

async def withdraw(key, address):
    try:
        account = Account(address=address,
                          client=GatewayClient(net='mainnet'),
                          key_pair=KeyPair.from_private_key(int(key[2:], 16)),
                          chain=StarknetChainId.MAINNET)
        amount_wei = await account.get_balance(zk_eth_address)
        amount = amount_wei / 10 ** 18
        logger.info(f'Starts to withdraw from zkLend {amount} of zkETH')
        current_nonce = await account.get_nonce()

        withdraw = Contract(
            address=zk_market_address,
            abi=ZK_LEND_ABI,
            provider=account,
        )

        withdraw_tx = withdraw.functions["withdraw_all"].prepare(
            eth_address
        )

        calls = [withdraw_tx]
        tx = await account.execute(calls=calls, auto_estimate=True,cairo_version=1,nonce=current_nonce)
        status = await account.client.wait_for_tx(tx.transaction_hash)
        if status.status.name in ['SUCCEEDED', 'ACCEPTED_ON_L1', 'ACCEPTED_ON_L2']:
            current_nonce += 1
            logger.success(
                f'{address} - транзакция подтвердилась, аккаунт успешно забрал ETH {scan}{hex(tx.transaction_hash)}')
            return 'updated'
        else:
            logger.error(f'{address} - транзакция неуспешна...')
            return 'error in tx'
    except Exception as e:
        error = str(e)
        if 'StarknetErrorCode.INSUFFICIENT_ACCOUNT_BALANCE' in error:
            logger.error(f'{address} - Не хватает баланса на деплой аккаунта...')
            return 'not balance'
        else:
            logger.error(f'{address} - ошибка {e}')
        return e
async def main():
    with open("keys.txt", "r") as f:
        keys = [row.strip() for row in f]
    with open("addresses.txt", "r") as f:
        addresses = [row.strip() for row in f]
    for address, key in zip(addresses, keys):
        logger.info('Начинаем срипт')
        if enable_deposite:
            await deposite(key,address)
        t = random.randint(*delay)
        logger.info(f'сплю {t} секунд')
        await asyncio.sleep(t)
        if enable_withdraw:
            await withdraw(key,address)
        logger.info('Закончили')
asyncio.run(main())