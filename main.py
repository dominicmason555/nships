import sys
import asyncio
import json
from typing import Optional

import transitions
import pysherasync
from asyncqt import QEventLoop, asyncSlot, asyncClose
from PySide2.QtCore import QFile
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QWidget


class MainWindow(QWidget):
    APP_KEY = "36f92e31b2fd7ce8666f"
    CLUSTER = "eu"

    def __init__(self):
        super().__init__()

        file = QFile("mainwindow.ui")
        file.open(QFile.ReadOnly)
        self.ui = QUiLoader().load(file, self)
        file.close()

        self.machine = transitions.Machine(model=self,
                                           states=["disconnected", "waiting", "placing", "aiming"],
                                           initial='disconnected',
                                           transitions=[{
                                               "trigger": "get_aim",
                                               "source": "waiting",
                                               "dest": "aiming"
                                           }, {
                                               "trigger": "fire",
                                               "source": "aiming",
                                               "dest": "waiting"
                                           }, {
                                               "trigger": "get_place",
                                               "source": "waiting",
                                               "dest": "placing"
                                           }, {
                                               "trigger": "place",
                                               "source": "placing",
                                               "dest": "waiting"
                                           }, {
                                               "trigger": "connect",
                                               "source": "disconnected",
                                               "dest": "waiting"
                                           }, {
                                               "trigger": "disconnect",
                                               "source": "*",
                                               "dest": "disconnected"
                                           }],
                                           auto_transitions=False,
                                           queued=True)

        self.disconnect_event = asyncio.Event()

        self.loop = asyncio.get_event_loop()

        self.ui.connect_btn.clicked.connect(self.try_connect)
        self.ui.input_edit.returnPressed.connect(self.handle_input)
        self.ui.execute_btn.clicked.connect(self.handle_input)

        self.pusher_client = pysherasync.PusherAsyncClient(self.APP_KEY, cluster=self.CLUSTER)
        self.client_task: Optional[asyncio.Task] = None
        # self.client.task = asyncio.Task(self.run_pusher_client("game_1"))
        self.ui.show()

    @asyncClose
    async def closeEvent(self):
        self.client_task.cancel()
        print("Shutting Down")

    @asyncSlot()
    async def try_connect(self):
        self.ui.output_edit.setHtml(f"Connecting...")

    @asyncSlot()
    async def handle_input(self):
        text = self.ui.input_edit.text()
        self.ui.output_edit.append(text)
        self.ui.input_edit.clear()

    async def run_pusher_client(self, chan_name: str):
        pusher_socket = await self.pusher_client.connect()
        status = await self.pusher_client.subscribe(channel_name=chan_name)
        print(f"Subscription Status: {status}")
        while True:
            if not pusher_socket.open:
                print("Connection reconnecting")
                pusher_socket = await self.pusher_client.connect()
                status = await self.pusher_client.subscribe(channel_name=chan_name)
                print(f"Subscription Status: {status}")
            try:
                msg = await pusher_socket.recv()
                msg = json.loads(msg)
                if msg:
                    print(msg)
                    self.ui.output_edit.append(f"Received: {msg['data']}")
            except Exception as e:
                print(e)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    mainWindow = MainWindow()
    with loop:
        sys.exit(loop.run_forever())
