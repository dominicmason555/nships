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
                                               "trigger": "server_connect",
                                               "source": "disconnected",
                                               "dest": "waiting",
                                               "after": "on_connect"
                                           }, {
                                               "trigger": "server_disconnect",
                                               "source": "*",
                                               "dest": "disconnected",
                                               "after": "on_disconnect"
                                           }],
                                           auto_transitions=False,
                                           queued=True)

        self.disconnect_event = asyncio.Event()

        self.loop = asyncio.get_event_loop()

        self.ui.connect_btn.clicked.connect(self.handle_connect_disconnect_btn)
        self.ui.input_edit.returnPressed.connect(self.handle_input)
        self.ui.execute_btn.clicked.connect(self.handle_input)

        self.pusher_client = pysherasync.PusherAsyncClient(self.APP_KEY, cluster=self.CLUSTER)
        self.client_task: Optional[asyncio.Task] = None
        self.connection_ready = asyncio.Event()
        self.pusher_socket = None
        self.ui.show()

    @asyncClose
    async def closeEvent(self):
        self.server_disconnect()
        self.client_task.cancel()
        await asyncio.sleep(1)
        print("Shutting Down")

    @asyncSlot()
    async def handle_connect_disconnect_btn(self):
        if self.is_disconnected():
            await self.try_connect()
        else:
            if self.client_task is not None:
                self.client_task.cancel()
                await self.pusher_socket.close()
            self.server_disconnect()

    async def try_connect(self):
        self.ui.output_edit.setHtml(f"Attempting connection...")
        chan_name = self.ui.server_edit.text()
        print(chan_name)
        self.client_task = asyncio.Task(self.run_pusher_client(chan_name))
        try:
            await asyncio.wait_for(self.connection_ready.wait(), 5)
            if self.pusher_socket is not None and self.pusher_socket.open:
                self.server_connect()
            else:
                self.server_disconnect()
        except asyncio.TimeoutError:
            self.ui.output_edit.append("Connection attempt timed out")
            print("Connection attempt timed out")
            self.server_disconnect()
        print(self.state)

    def on_connect(self):
        print("on_connect")
        self.ui.output_edit.append("Connected")
        self.ui.connect_btn.setText("Disconnect")

    def on_disconnect(self):
        print("on_disconnect")
        self.connection_ready.clear()
        self.ui.output_edit.append("Disconnected")
        self.ui.connect_btn.setText("Connect")

    @asyncSlot()
    async def handle_input(self):
        text = self.ui.input_edit.text()
        self.ui.output_edit.append(text)
        self.ui.input_edit.clear()

    async def run_pusher_client(self, chan_name: str):
        print("Client Starting")
        if self.pusher_socket is None or not self.pusher_socket.open:
            print("Connecting...")
            self.pusher_socket = await self.pusher_client.connect()
            status = await self.pusher_client.subscribe(channel_name=chan_name)
            print(f"Subscription Status: {status}")
            if status["event"] == "pusher:connection_established":
                self.connection_ready.set()
        while self.pusher_socket.open:
            try:
                msg = await self.pusher_socket.recv()
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
