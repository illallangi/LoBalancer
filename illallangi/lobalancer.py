from os.path import basename
from sys import argv, stderr
from time import sleep

from click import Choice as CHOICE, INT, STRING, command, option

from loguru import logger

from pyroute2 import NDB

from socket import socket, error


ndb = NDB()


@command()
@option('--log-level',
        envvar='LOG_LEVEL',
        type=CHOICE(['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'SUCCESS', 'TRACE'],
                    case_sensitive=False),
        default='INFO')
@option('--sleep-time',
        type=INT,
        default=5)
@option('--port',
        type=INT,
        envvar='PORT',
        required=True)
@option('--ip',
        type=STRING,
        default='127.0.0.1')
@option('--vip',
        type=STRING,
        envvar='ADDRESS',
        required=True)
def LoBalancer(log_level,
               sleep_time,
               port,
               ip,
               vip):
    logger.remove()
    logger.add(stderr, level=log_level)

    logger.success(f'{basename(argv[0])} Started')
    logger.info(f'  --log-level "{log_level}"')
    logger.info(f'  --sleep-time {sleep_time}')
    logger.info(f'  --port {port}')
    logger.info(f'  --ip "{ip}"')
    logger.info(f'  --vip "{vip}"')

    while True:
        h = health_check(ip, port)
        logger.info(f'Health check on {ip}:{port} returned {h}')

        v = vip_check(vip)
        logger.info(f'VIP check for {vip} returned {v}')

        if h and not v:
            logger.info(f'Adding VIP {vip}')
            add_vip(vip)
        elif not h and v:
            logger.info(f'Removing VIP {vip}')
            remove_vip(vip)
        else:
            logger.info(f'No action required')

        if sleep_time == 0:
            break

        logger.info(f'Sleeping {sleep_time} seconds')
        sleep(sleep_time)


def health_check(ip, port):
    s = socket()
    logger.debug(f'Attempting to connect to {ip}:{port}')
    try:
        s.connect((ip, port))
        logger.debug(f'Connected to {ip}:{port}')
        return True
    except error as e:
        logger.debug(f'Connection to {ip}:{port} failed: {e}')
        return False
    finally:
        s.close()


def vip_check(vip):
    return vip in [s.address for s in ndb.addresses.summary()]


def add_vip(vip):
    return ndb.interfaces['lo'].add_ip(f'{vip}/32').commit()


def remove_vip(vip):
    return ndb.addresses[f'{vip}/32'].remove().commit()


if __name__ == "__main__":
    LoBalancer()
