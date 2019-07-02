import sys
import asyncio
import json
import aiohttp

import pynng
import pysherasync
from asyncqt import QEventLoop, asyncSlot, asyncClose
from sniffio import current_async_library_cvar
from PySide2.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
    QVBoxLayout)


class MainWindow(QWidget):
    _DEF_URL = 'https://jsonplaceholder.typicode.com/todos/1'
    _SESSION_TIMEOUT = 1.
    _APP_KEY = "36f92e31b2fd7ce8666f"
    _CLUSTER = "eu"

    def __init__(self):
        super().__init__()

        self.setLayout(QVBoxLayout())

        self.loop = asyncio.get_event_loop()

        self.lblStatus = QLabel('Idle', self)
        self.layout().addWidget(self.lblStatus)

        self.editUrl = QLineEdit(self._DEF_URL, self)
        self.layout().addWidget(self.editUrl)

        self.editResponse = QTextEdit('', self)
        self.layout().addWidget(self.editResponse)

        self.btnFetch = QPushButton('Fetch', self)
        self.btnFetch.clicked.connect(self.on_btn_fetch_clicked)
        self.layout().addWidget(self.btnFetch)

        self.session = aiohttp.ClientSession(
            loop=self.loop,
            timeout=aiohttp.ClientTimeout(total=self._SESSION_TIMEOUT))

        self.loop.create_task(self.ping())
        self.loop.create_task(self.serve())
        self.loop.create_task(self.pusher_client())

    @asyncClose
    async def closeEvent(self, event):
        await self.session.close()

    @asyncSlot()
    async def on_btn_fetch_clicked(self):
        self.btnFetch.setEnabled(False)
        self.lblStatus.setText('Fetching...')

        try:
            async with self.session.get(self.editUrl.text()) as r:
                self.editResponse.setText(await r.text())
        except Exception as exc:
            self.lblStatus.setText('Error: {}'.format(exc))
        else:
            self.lblStatus.setText('Finished!')
        finally:
            self.btnFetch.setEnabled(True)

    async def ping(self):
        i = 0
        while True:
            i += 1
            print(f"Ping {i}")
            await asyncio.sleep(15)

    async def serve(self):
        with pynng.Rep0(listen="tcp://0.0.0.0:5555") as s:
            while True:
                msg = await s.arecv()
                print(f"Received: {msg.decode()}")
                self.editResponse.append(f"Received: {msg.decode()}")
                s.send(msg)

    async def pusher_client(self):
        pusher_client = pysherasync.PusherAsyncClient(self._APP_KEY, cluster=self._CLUSTER)
        pusher_socket = await pusher_client.connect()
        status = await pusher_client.subscribe(channel_name='my-channel')
        print(f"Subscription Status: {status}")

        while True:
            if not pusher_socket.open:
                print("Connection reconnecting")
                pusher_socket = await pusher_client.connect()
                status = await pusher_client.subscribe(channel_name='my-channel')
                print(f"Subscription Status: {status}")
            try:
                msg = await pusher_socket.recv()
                msg = json.loads(msg)
                if msg:
                    print(msg)
                    self.editResponse.append(f"Received: {msg['data']}")
            except Exception as e:
                print(e)


if __name__ == '__main__':
    token = None
    try:
        token = current_async_library_cvar.set("asyncio")
        app = QApplication(sys.argv)
        loop = QEventLoop(app)
        asyncio.set_event_loop(loop)

        mainWindow = MainWindow()
        mainWindow.show()
        with loop:
            sys.exit(loop.run_forever())
    finally:
        current_async_library_cvar.reset(token)
