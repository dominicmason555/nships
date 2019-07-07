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
@click.option("-m", "--message", prompt=True, help="The message to send", default="Fired at (0,0)")
@click.option("-c", "--channel", prompt=True, help="The channel to send to", default="game_1")
@click.option("-e", "--event", prompt=True, help="The event name to trigger", default="fire")
def main(message, channel, event):
    pusher_client.trigger(channel, event, {'message': message})


if __name__ == "__main__":
    main()
