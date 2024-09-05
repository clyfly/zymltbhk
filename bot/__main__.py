from aiofiles import open as aiopen
from aiofiles.os import path as aiopath, remove
from asyncio import gather, create_subprocess_exec
from os import execl as osexecl
from psutil import (
    disk_usage,
    cpu_percent,
    swap_memory,
    cpu_count,
    virtual_memory,
    net_io_counters,
    boot_time,
)
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from signal import signal, SIGINT
from sys import executable
from time import time

from bot import (
    bot,
    botStartTime,
    LOGGER,
    Intervals,
    DATABASE_URL,
    INCOMPLETE_TASK_NOTIFIER,
    scheduler,
)
from .helper.ext_utils.bot_utils import cmd_exec, sync_to_async, create_help_buttons
from .helper.ext_utils.db_handler import DbManager
from .helper.ext_utils.files_utils import clean_all, exit_clean_up
from .helper.ext_utils.jdownloader_booter import jdownloader
from .helper.ext_utils.status_utils import get_readable_file_size, get_readable_time
from .helper.ext_utils.telegraph_helper import telegraph
from .helper.listeners.aria2_listener import start_aria2_listener
from .helper.mirror_leech_utils.rclone_utils.serve import rclone_serve_booter
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.button_build import ButtonMaker
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.message_utils import sendMessage, editMessage, sendFile
from .modules.func import *
from .modules import (
    authorize,
    broadcast,
    cancel_task,
    clone,
    exec,
    gd_count,
    gd_delete,
    gd_search,
    mirror_leech,
    status,
    torrent_search,
    torrent_select,
    ytdlp,
    rss,
    shell,
    users_settings,
    bot_settings,
    help,
    force_start,
)


async def restart(_, message):
    Intervals["stopAll"] = True
    restart_message = await sendMessage(message, "Restarting...")
    if scheduler.running:
        scheduler.shutdown(wait=False)
    if qb := Intervals["qb"]:
        qb.cancel()
    if jd := Intervals["jd"]:
        jd.cancel()
    if st := Intervals["status"]:
        for intvl in list(st.values()):
            intvl.cancel()
    await sync_to_async(clean_all)
    proc1 = await create_subprocess_exec(
        "pkill", "-9", "-f", "gunicorn|aria2c|ffmpeg|rclone|java"
    )
    proc2 = await create_subprocess_exec("python3", "update.py")
    await gather(proc1.wait(), proc2.wait())
    async with aiopen(".restartmsg", "w") as f:
        await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    osexecl(executable, executable, "-m", "bot")


async def ping(_, message):
    start_time = int(round(time() * 1000))
    reply = await sendMessage(message, "Starting Ping")
    end_time = int(round(time() * 1000))
    await editMessage(reply, f"{end_time - start_time} ms")


async def log(_, message):
    await sendFile(message, "log.txt")


help_string = f"""
NOTE: Coba setiap command tanpa argumen untuk info lebih lanjut.
<blockquote expandable>
<b>Mirroring Commands 🔄</b>
/{BotCommands.MirrorCommand[0]} or /{BotCommands.MirrorCommand[1]}: Mulai mirror ke cloud.
/{BotCommands.QbMirrorCommand[0]} or /{BotCommands.QbMirrorCommand[1]}: Mirror ke cloud pake qBittorrent.
/{BotCommands.JdMirrorCommand[0]} or /{BotCommands.JdMirrorCommand[1]}: Mirror ke cloud pake JDownloader.
/{BotCommands.NzbMirrorCommand[0]} or /{BotCommands.NzbMirrorCommand[1]}: Mirror ke cloud pake Sabnzbd.
/{BotCommands.YtdlCommand[0]} or /{BotCommands.YtdlCommand[1]}: Mirror link yt-dlp.

<b>Leeching Commands 📥</b>
/{BotCommands.LeechCommand[0]} or /{BotCommands.LeechCommand[1]}: Mulai leech ke Telegram.
/{BotCommands.QbLeechCommand[0]} or /{BotCommands.QbLeechCommand[1]}: Leech pake qBittorrent.
/{BotCommands.JdLeechCommand[0]} or /{BotCommands.JdLeechCommand[1]}: Leech pake JDownloader.
/{BotCommands.NzbLeechCommand[0]} or /{BotCommands.NzbLeechCommand[1]}: Leech pake Sabnzbd.
/{BotCommands.YtdlLeechCommand[0]} or /{BotCommands.YtdlLeechCommand[1]}: Leech link yt-dlp.

<b>Google Drive Commands ☁️</b>
/{BotCommands.CloneCommand} [drive_url]: Copy file/folder ke Google Drive.
/{BotCommands.CountCommand} [drive_url]: Hitung file/folder di Google Drive.
/{BotCommands.DeleteCommand} [drive_url]: Hapus file/folder dari Google Drive (Hanya Owner & Sudo).

<b>Settings Commands ⚙️</b>
/{BotCommands.UserSetCommand[0]} or /{BotCommands.UserSetCommand[1]} [query]: Setting pengguna.
/{BotCommands.BotSetCommand[0]} or /{BotCommands.BotSetCommand[1]} [query]: Setting bot.

<b>Task Management Commands 🗂️</b>
/{BotCommands.SelectCommand}: Pilih file dari torrents atau nzb pake gid atau balasan.
/{BotCommands.CancelTaskCommand[0]} or /{BotCommands.CancelTaskCommand[1]} [gid]: Batalin task pake gid atau balasan.
/{BotCommands.ForceStartCommand[0]} or /{BotCommands.ForceStartCommand[1]} [gid]: Paksa mulai task pake gid atau balasan.
/{BotCommands.CancelAllCommand} [query]: Batalin semua task [status].

<b>Search Commands 🔍</b>
/{BotCommands.ListCommand} [query]: Cari di Google Drive(s).
/{BotCommands.SearchCommand} [query]: Cari torrents pake API.

<b>Status & Stats Commands 📊</b>
/{BotCommands.StatusCommand}: Tunjukin status semua download.
/{BotCommands.StatsCommand}: Tunjukin statistik mesin bot.
/{BotCommands.PingCommand}: Cek ping ke bot (Hanya Owner & Sudo).

<b>Authorization Commands 🔑</b>
/{BotCommands.AuthorizeCommand}: Otorisasi chat atau pengguna (Hanya Owner & Sudo).
/{BotCommands.UnAuthorizeCommand}: Cabut otorisasi chat atau pengguna (Hanya Owner & Sudo).
/{BotCommands.UsersCommand}: Tunjukin setting pengguna (Hanya Owner & Sudo).

<b>Owner-Specific Commands 👑</b>
/{BotCommands.AddSudoCommand}: Tambahin sudo user (Hanya Owner).
/{BotCommands.RmSudoCommand}: Hapus sudo users (Hanya Owner).
/{BotCommands.RestartCommand}: Restart dan update bot (Hanya Owner & Sudo).
/{BotCommands.LogCommand}: Dapetin log file bot (Hanya Owner & Sudo).
/{BotCommands.ShellCommand}: Jalankan shell commands (Hanya Owner).
/{BotCommands.AExecCommand}: Eksekusi fungsi async (Hanya Owner).
/{BotCommands.ExecCommand}: Eksekusi fungsi sync (Hanya Owner).
/{BotCommands.ClearLocalsCommand}: Bersihin {BotCommands.AExecCommand} atau {BotCommands.ExecCommand} locals (Hanya Owner).

<b>RSS Commands 📡</b>
/{BotCommands.RssCommand}: Menu RSS.
</blockquote>
"""


async def bot_help(_, message):
    await sendMessage(message, help_string)


async def restart_notification():
    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
    else:
        chat_id, msg_id = 0, 0

    async def send_incompelete_task_message(cid, msg):
        try:
            if msg.startswith("Restarted Successfully!"):
                await bot.edit_message_text(
                    chat_id=chat_id, message_id=msg_id, text=msg
                )
                await remove(".restartmsg")
            else:
                await bot.send_message(
                    chat_id=cid,
                    text=msg,
                    disable_web_page_preview=True,
                    disable_notification=True,
                )
        except Exception as e:
            LOGGER.error(e)

    if INCOMPLETE_TASK_NOTIFIER and DATABASE_URL:
        if notifier_dict := await DbManager().get_incomplete_tasks():
            for cid, data in notifier_dict.items():
                msg = "Restarted Successfully!" if cid == chat_id else "Bot Restarted!"
                for tag, links in data.items():
                    msg += f"\n\n{tag}: "
                    for index, link in enumerate(links, start=1):
                        msg += f" <a href='{link}'>{index}</a> |"
                        if len(msg.encode()) > 4000:
                            await send_incompelete_task_message(cid, msg)
                            msg = ""
                if msg:
                    await send_incompelete_task_message(cid, msg)

    if await aiopath.isfile(".restartmsg"):
        try:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id, text="Restarted Successfully!"
            )
        except:
            pass
        await remove(".restartmsg")


async def main():
    jdownloader.initiate()
    await gather(
        sync_to_async(clean_all),
        torrent_search.initiate_search_tools(),
        restart_notification(),
        telegraph.create_account(),
        rclone_serve_booter(),
        sync_to_async(start_aria2_listener, wait=False),
        set_commands(bot)
    )
    create_help_buttons()
    bot.add_handler(
        MessageHandler(
            restart, filters=command(BotCommands.RestartCommand) & CustomFilters.sudo
        )
    )
    bot.add_handler(
        MessageHandler(
            ping, filters=command(BotCommands.PingCommand) & CustomFilters.authorized
        )
    )
    bot.add_handler(
        MessageHandler(
            bot_help,
            filters=command(BotCommands.HelpCommand) & CustomFilters.authorized,
        )
    )
    LOGGER.info("Bot Started!")
    signal(SIGINT, exit_clean_up)


bot.loop.run_until_complete(main())
bot.loop.run_forever()
