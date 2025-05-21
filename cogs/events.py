def register_events(client, is_prod, leaderboard_manager,voice_cog):
    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        if is_prod:
            if not leaderboard_manager.auto_leaderboard.is_running():
                leaderboard_manager.auto_leaderboard.start()
                print("Auto leaderboard started")
            if not leaderboard_manager.update_leaderboard_days_task.is_running():
                await leaderboard_manager.update_leaderboard_days()
                leaderboard_manager.update_leaderboard_days_task.start()
            if voice_cog and not voice_cog.check_vc_task.is_running():
                voice_cog.start_tasks()
        else:
            print("Auto leaderboard and voice channel checks are disabled in development mode.")

    @client.event
    async def on_message(message):
        if message.author.id != 1117105897710305330:
            pass
