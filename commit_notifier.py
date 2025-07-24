import aiohttp
import json
import os
import discord
from datetime import datetime

# Configuration
GITHUB_REPO_OWNER = "Aquatictw"  # Replace with your GitHub username
GITHUB_REPO_NAME = "121armybot"  # Replace with your repository name
COMMIT_CHANNEL_ID = 1389936899917090877  # Replace with your channel ID
SENT_COMMITS_FILE = "sent_commits.json"


class CommitNotifier:
    def __init__(self, bot):
        self.bot = bot

    async def load_sent_commits(self):
        """Load the list of already sent commit SHAs"""
        if os.path.exists(SENT_COMMITS_FILE):
            with open(SENT_COMMITS_FILE, "r") as f:
                return json.load(f)
        return []

    async def save_sent_commits(self, commits):
        """Save the list of sent commit SHAs"""
        with open(SENT_COMMITS_FILE, "w") as f:
            json.dump(commits, f)

    async def fetch_latest_commits(self):
        """Fetch latest commits from GitHub API"""
        url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/commits"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params={"per_page": 5}) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"GitHub API error: {response.status}")
                        return []
            except Exception as e:
                print(f"Error fetching commits: {e}")
                return []

    def format_commit_message(self, commit):
        """Format commit information for Discord"""
        sha = commit["sha"][:7]  # Short SHA
        message = commit["commit"]["message"].split("\n")[0]  # First line only
        author = commit["commit"]["author"]["name"]
        date = commit["commit"]["author"]["date"]
        url = commit["html_url"]

        # Parse and format the date
        commit_date = datetime.fromisoformat(date.replace("Z", "+00:00"))
        formatted_date = commit_date.strftime("%Y-%m-%d %H:%M UTC")

        return f"🚀 **[{sha}]({url})** {message}\n👤 {author} • 📅 {formatted_date}"

    async def check_and_notify_commits(self):
        """Main function to check for new commits and send notifications"""
        try:
            channel = self.bot.get_channel(COMMIT_CHANNEL_ID)
            if not channel:
                print(f"Could not find channel with ID {COMMIT_CHANNEL_ID}")
                return

            sent_commits = await self.load_sent_commits()
            latest_commits = await self.fetch_latest_commits()

            if not latest_commits:
                return

            new_commits = []
            for commit in reversed(latest_commits):  # Process oldest first
                if commit["sha"] not in sent_commits:
                    new_commits.append(commit)
                    sent_commits.append(commit["sha"])

            if new_commits:
                # Send header message
                embed = discord.Embed(
                    title="🔄 Bot Updated!",
                    description=f"Found {len(new_commits)} new commit(s) since last startup:",
                    color=0x00FF00,
                    timestamp=datetime.utcnow(),
                )
                embed.set_footer(
                    text=f"Repository: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}"
                )

                await channel.send(embed=embed)

                # Send individual commit messages
                for commit in new_commits:
                    commit_msg = self.format_commit_message(commit)

                    # Create embed for each commit
                    commit_embed = discord.Embed(description=commit_msg, color=0x0099FF)

                    await channel.send(embed=commit_embed)

                # Save updated list
                await self.save_sent_commits(sent_commits)
                print(f"Sent {len(new_commits)} new commit notifications")
            else:
                print("No new commits to report")

        except Exception as e:
            print(f"Error in commit notification: {e}")
