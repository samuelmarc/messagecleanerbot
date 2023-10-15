import asyncio
import logging
import math
import os

import uvloop
from pyrogram import Client, filters, idle
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.errors import ChatAdminRequired, UserNotParticipant
from pyrogram.raw.functions.messages import DeleteHistory
from pyrogram.raw.functions.account import UpdateStatus
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, ChatPrivileges

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')
helper_session_string = os.getenv('SESSION_STRING')

uvloop.install()

client = Client(
    name='msgcleanerbot',
    api_id=api_id,
    api_hash=api_hash,
    bot_token=bot_token
)

client2 = Client(
    name='msgcleanerhelp',
    api_id=api_id,
    api_hash=api_hash,
    in_memory=True,
    session_string=helper_session_string
)


@client2.on_message(filters.private)
async def on_priv_msg(cl: Client, m: Message):
    await m.from_user.block()
    await cl.invoke(
        DeleteHistory(
            peer=await cl.resolve_peer(peer_id=m.from_user.id),
            max_id=0,
            revoke=True
        )
    )


@client.on_message(filters.command('start') & filters.private)
async def start(cl: Client, m: Message):
    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text='➕ Add me to a group',
                    url=f'tg://resolve?domain={cl.me.username}&startgroup=&admin=manage_chat+promote_members+invite_users+delete_messages+restrict_members'
                )
            ],
            [
                InlineKeyboardButton(
                    text='➕ Add me to a channel',
                    url=f'tg://resolve?domain={cl.me.username}&startchannel=&admin=manage_chat+promote_members+invite_users+post_messages+delete_messages'
                )
            ],
            [
                InlineKeyboardButton(
                    text='📦 Source code',
                    url=f'https://github.com/samuelmarc/messagecleanerbot'
                )
            ]
        ]
    )
    await m.reply(
        text=f'Hello {m.from_user.mention} I am the bot that can <b>delete all messages from your channel or group created by @samuel_ks</b>, just add me to your channel or group, and start using, I also have a public repository.',
        reply_markup=reply_markup
    )


@client.on_message(filters.command('help'))
async def help(_, m: Message):
    await m.reply(
        text="Need help? To use the bot it's very simple, just add me to your channel or group with the following permissions:\n\n<b>For Channel:</b>\n— <i>Post Messages</i>\n— <i>Delete messages from others</i>\n— <i>Add Members</i>\n— <i>Add Admins</i>\n\n<b>For Group:</b>\n— <i>Delete Messages</i>\n— <i>Ban Users</i>\n— <i>Invite users via link</i>\n— <i>Add Admins</i>\n\nAlso remember that the user executing the command must be an administrator and have permission to delete messages, after that just execute the <code>/delall</code> command, wait and that's it."
    )


@client.on_message(filters.command('delall') & (filters.group | filters.channel))
async def delall(cl: Client, m: Message):
    if m.chat.type == ChatType.GROUP:
        await m.reply('❌ Unfortunately normal groups are not supported, only supergroups.')
        await m.chat.leave()
    else:
        try:
            user_req_member = await m.chat.get_member(m.from_user.id)
            user_req_member_privileges = user_req_member.privileges
        except AttributeError:
            user_req_member_privileges = ChatPrivileges(can_delete_messages=True)
        if user_req_member_privileges:
            if user_req_member_privileges.can_delete_messages:
                m.chat = await cl.get_chat(m.chat.id)
                invite_link = m.chat.invite_link
                me_member = await m.chat.get_member(cl.me.id)
                me_member_privileges = me_member.privileges
                if me_member_privileges:
                    if m.chat.type == ChatType.SUPERGROUP:
                        if me_member_privileges.can_promote_members is False or me_member_privileges.can_invite_users is False or me_member_privileges.can_delete_messages is False or me_member_privileges.can_restrict_members is False:
                            await m.reply(
                                '❌ You need to give me the appropriate admin permissions, see the <code>/help</code> command for more information.'
                            )
                            return
                    elif m.chat.type == ChatType.CHANNEL:
                        if me_member_privileges.can_promote_members is False or me_member_privileges.can_invite_users is False or me_member_privileges.can_post_messages is False or me_member_privileges.can_delete_messages is False:
                            try:
                                await m.reply(
                                    '❌ You need to give me the appropriate admin permissions, see the <code>/help</code> command for more information.'
                                )
                            except ChatAdminRequired:
                                await m.chat.leave()
                            return
                    client2_user_id = client2.me.id
                    try:
                        helper_member = await m.chat.get_member(client2_user_id)
                        helper_member_status = helper_member.status
                        helper_member_privileges = helper_member.privileges
                    except UserNotParticipant:
                        await client2.join_chat(invite_link)
                        await m.chat.promote_member(
                            user_id=client2_user_id,
                            privileges=ChatPrivileges(
                                can_delete_messages=True
                            )
                        )
                        helper_member_status = ChatMemberStatus.ADMINISTRATOR
                        helper_member_privileges = ChatPrivileges(can_delete_messages=True)
                    if helper_member_status == ChatMemberStatus.BANNED:
                        try:
                            await m.chat.unban_member(client2_user_id)
                            await client2.join_chat(invite_link)
                            await m.chat.promote_member(
                                user_id=client2_user_id,
                                privileges=ChatPrivileges(
                                    can_delete_messages=True
                                )
                            )
                        except ChatAdminRequired:
                            await m.reply('❌ The Helper User is banned.')
                    else:
                        if not helper_member_privileges or helper_member_privileges.can_delete_messages is False:
                            await m.chat.promote_member(
                                user_id=client2_user_id,
                                privileges=ChatPrivileges(
                                    can_delete_messages=True
                                )
                            )
                        chat_history_count = await client2.get_chat_history_count(m.chat.id)
                        if chat_history_count <= 100:
                            message_ids = []
                            async for message in client2.get_chat_history(m.chat.id, 100):
                                message_ids.append(message.id)
                            await client2.delete_messages(m.chat.id, message_ids)
                        else:
                            loops_count = math.ceil(chat_history_count / 100)
                            for loop_num in range(loops_count):
                                message_ids = []
                                async for message in client2.get_chat_history(m.chat.id, 100):
                                    message_ids.append(message.id)
                                await client2.delete_messages(m.chat.id, message_ids)
                                await asyncio.sleep(3)
                        await client2.leave_chat(m.chat.id, True)
                        await m.chat.leave()
                else:
                    try:
                        await m.reply(
                            '❌ You need to give me the appropriate admin permissions, see the <code>/help</code> command for more information.'
                        )
                    except ChatAdminRequired:
                        await m.chat.leave()
            else:
                await m.reply('❌ You are not allowed to delete messages as admin.')
        else:
            await m.reply('❌ You are not a group administrator and cannot run this command.')


async def main():
    await client.start()
    logging.warning('⚡️ Bot Started!')
    await client2.start()
    client2.me = await client2.get_me()
    await client2.invoke(
    	UpdateStatus(
    		offline=False
    	)
    )
    logging.warning('🔧 User Helper Started!')
    await idle()
    await client.stop()
    logging.warning('🔌 Bot Stopped.')
    await client2.invoke(
    	UpdateStatus(
    		offline=True
    	)
    )
    await client2.stop()
    logging.warning('🔌 User Helper Stopped.')


if __name__ == '__main__':
    event_policy = asyncio.get_event_loop_policy()
    event_loop = event_policy.get_event_loop()
    try:
        event_loop.run_until_complete(main())
    finally:
        event_loop.close()
