import os
import sys
import psycopg2
import requests
import textwrap
import logging
from prettytable import PrettyTable
from math import ceil
from typing import List, Optional, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Constants (Can be moved to a separate config file or environment variables)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "your_database_name")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password")
GITHUB_PERSONAL_TOKEN = os.getenv("GITHUB_PERSONAL_TOKEN", "")

# Database connection function
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logging.info("Successfully connected to the PostgreSQL database.")
        return conn
    except psycopg2.Error as e:
        logging.error(f"Error connecting to the database: {e}")
        sys.exit(1)

# Function to get available users
def get_available_users(conn, username: str) -> Dict[str, int]:
    """
    Check the count of existing users and repositories in the database.

    :param conn: Active database connection.
    :param username: GitHub username to check.
    :return: Dictionary with counts of existing users and repositories.
    """
    counts = {'users': 0, 'repos': 0}
    try:
        with conn.cursor() as cursor:
            # Count users
            cursor.execute("SELECT COUNT(*) FROM user_data WHERE username = %s;", (username,))
            counts['users'] = cursor.fetchone()[0]
            logging.debug(f"Existing users count: {counts['users']}")

            # Count repositories
            cursor.execute("SELECT COUNT(*) FROM repositories WHERE username = %s;", (username,))
            counts['repos'] = cursor.fetchone()[0]
            logging.debug(f"Existing repositories count: {counts['repos']}")
    except psycopg2.Error as e:
        logging.error(f"Database query error: {e}")
    return counts

# Function to get user data from GitHub
def get_user_data_github(username: str) -> Optional[Dict]:
    """
    Fetch user data from GitHub API.

    :param username: GitHub username.
    :return: Dictionary containing user data or None if failed.
    """
    url = f"https://api.github.com/users/{username}"
    headers = {
        "Authorization": f"Bearer {GITHUB_PERSONAL_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "py-github-project"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            logging.info(f"Successfully fetched data for user '{username}'.")
            return response.json()
        else:
            logging.error(f"Failed to fetch data for user '{username}'. Status Code: {response.status_code}, Response: {response.text}")
            return None
    except requests.RequestException as e:
        logging.error(f"Request exception: {e}")
        return None

# Function to get repository details from GitHub
def get_repository_details_github(username: str, per_page: int) -> Optional[List[Dict]]:
    """
    Fetch repository details from GitHub API with pagination.

    :param username: GitHub username.
    :param per_page: Number of repositories per page.
    :return: List of repository dictionaries or None if failed.
    """
    repositories = []
    page = 1
    try:
        # First, get the total number of public repositories to calculate total pages
        user_data = get_user_data_github(username)
        if not user_data:
            return None
        total_repos = user_data.get('public_repos', 0)
        total_pages = ceil(total_repos / per_page)
        logging.info(f"Total public repositories: {total_repos}, Total pages: {total_pages}")

        while page <= total_pages:
            url = f"https://api.github.com/users/{username}/repos"
            params = {
                "type": "owner",
                "per_page": per_page,
                "page": page
            }
            headers = {
                "Authorization": f"Bearer {GITHUB_PERSONAL_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "py-github-project"
            }
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                repos_page = response.json()
                repositories.extend(repos_page)
                logging.debug(f"Fetched page {page} with {len(repos_page)} repositories.")
                page += 1
            else:
                logging.error(f"Failed to fetch repositories on page {page}. Status Code: {response.status_code}, Response: {response.text}")
                return None
        return repositories
    except requests.RequestException as e:
        logging.error(f"Request exception while fetching repositories: {e}")
        return None

# Function to write user data into the database
def write_user_data(conn, username: str, user_email: Optional[str], location: Optional[str]):
    """
    Insert user data into the user_data table.

    :param conn: Active database connection.
    :param username: GitHub username.
    :param user_email: User's email.
    :param location: User's location.
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO user_data (username, email, location) VALUES (%s, %s, %s);",
                (username, user_email, location)
            )
            conn.commit()
            logging.info(f"Inserted data for user '{username}' into user_data table.")
    except psycopg2.Error as e:
        conn.rollback()
        logging.error(f"Error inserting user data: {e}")

# Function to write repositories into the database
def write_repositories(conn, username: str, repositories: List[Dict]):
    """
    Insert repository data into the repositories table.

    :param conn: Active database connection.
    :param username: GitHub username.
    :param repositories: List of repository dictionaries.
    """
    try:
        with conn.cursor() as cursor:
            for repo in repositories:
                name = repo.get('name', 'No Name')
                description = repo.get('description', 'No Description')
                language = repo.get('language', 'Unknown')
                cursor.execute(
                    "INSERT INTO repositories (name, description, languages, username) VALUES (%s, %s, %s, %s);",
                    (name, description, language, username)
                )
            conn.commit()
            logging.info(f"Inserted {len(repositories)} repositories for user '{username}' into repositories table.")
    except psycopg2.Error as e:
        conn.rollback()
        logging.error(f"Error inserting repositories: {e}")

# Function to print output using PrettyTable
def print_output(conn, username: str):
    """
    Fetch and print user and repository data from the database.

    :param conn: Active database connection.
    :param username: GitHub username.
    """
    try:
        with conn.cursor() as cursor:
            # Fetch user details
            cursor.execute("SELECT username, email FROM user_data WHERE username = %s;", (username,))
            user_det = cursor.fetchone()
            if user_det:
                logging.info(f"User Name: {user_det[0]}")
                logging.info(f"Email: {user_det[1]}")
            else:
                logging.warning(f"No user data found for username '{username}'.")

            # Fetch repository details
            cursor.execute("SELECT name, description FROM repositories WHERE username = %s;", (username,))
            repos = cursor.fetchall()

            if repos:
                logging.info("Public Repositories:")
                table = PrettyTable(['Name', 'Description'])
                for repo in repos:
                    name, description = repo
                    description = description if description else 'N/A'
                    wrapped_description = textwrap.wrap(description, width=120) or ['N/A']

                    # Add the first line with the repository name
                    table.add_row([name, wrapped_description[0]])

                    # Add subsequent lines without the repository name
                    for line in wrapped_description[1:]:
                        table.add_row(['', line])
                print(table)
            else:
                logging.info(f"No repositories found for user '{username}'.")
    except psycopg2.Error as e:
        logging.error(f"Error fetching data for output: {e}")

# Function to process user repositories
def process_user_repos(conn, username: str, per_page: int = 3):
    """
    Process and store user repositories from GitHub into the database.

    :param conn: Active database connection.
    :param username: GitHub username.
    :param per_page: Number of repositories per page.
    """
    repositories = get_repository_details_github(username, per_page)
    if repositories is not None:
        write_repositories(conn, username, repositories)
        print_output(conn, username)
    else:
        logging.error("Failed to retrieve repositories.")

# Main function
def main():
    """
    Main entry point of the script.
    """
    # Prompt user for GitHub username
    username = input("Enter GitHub username: ").strip()
    if not username:
        logging.error("No username entered. Exiting.")
        sys.exit(1)

    logging.info(f"Username entered: {username}")

    # Initialize database connection
    conn = get_db_connection()

    try:
        # Check existing users and repositories
        counts = get_available_users(conn, username)
        existing_users = counts['users']
        existing_repos = counts['repos']

        if existing_users > 0:
            logging.info(f"User '{username}' already exists in user_data table.")
            if existing_repos > 0:
                logging.info(f"User '{username}' already has repositories in repositories table.")
                print_output(conn, username)
            else:
                logging.info(f"No repositories found for user '{username}'. Fetching from GitHub...")
                process_user_repos(conn, username)
        else:
            # Fetch user data from GitHub
            userdata = get_user_data_github(username)
            if userdata:
                user_email = userdata.get('email', 'N/A')
                location = userdata.get('location', 'N/A')
                write_user_data(conn, username, user_email, location)
                process_user_repos(conn, username)
            else:
                logging.error(f"User '{username}' data could not be fetched from GitHub.")
    finally:
        # Ensure the database connection is closed
        conn.close()
        logging.info("Database connection closed.")

if __name__ == "__main__":
    main()
