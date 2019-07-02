import pusher
import click

pusher_client = pusher.Pusher(
  app_id='815864',
  key='36f92e31b2fd7ce8666f',
  secret='d0da0fd108c7baac6959',
  cluster='eu',
  ssl=True
)


@click.command()
@click.option("-m", "--message", prompt=True, help="The message to send", default="Test Message")
def main(message):
    pusher_client.trigger('my-channel', 'my-event', {'message': message})


if __name__ == "__main__":
    main()
