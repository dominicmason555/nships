import pynng
import click


@click.command()
@click.option("-m", "--message", prompt=True, help="The message to send", default="Test Message")
@click.option("-a", "--address", prompt=True, help="The address to send to", default="tcp://127.0.0.1:5555")
def send_plain(message, address):
    with pynng.Req0(dial=address, send_timeout=1000) as s:
        try:
            s.send(message.encode("UTF-8"))
            resp = s.recv()
            print(f"Response: {resp.decode()}")
        except pynng.exceptions.Timeout:
            print("Message send timeout reached")


if __name__ == "__main__":
    send_plain()

