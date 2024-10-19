#Import libraries 
import psycopg2, requests, textwrap,sys,logging
from prettytable import PrettyTable
from typing import List,Optional,Dict
import math

#global variable 

GITHUB_PERSONAL_TOKEN=input(f"input the git token:")

# configure logging 
logging.basicConfig(
    level=logging.INFO,
    format ='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)


# Database connection function

def get_database_connection():
    try:        
        '''
        connect to postgres
        '''
        

        ''' Connection parameters '''
        db_host = "localhost"  # or the IP address of the host if connecting remotely
        db_port = "5432"
        db_name = "your_database_name"
        db_user = "postgres"
        db_password = "your_password"

        ''' Connect to the PostgreSQL database'''

        connection = psycopg2.connect(
            host="localhost",
            port="5432",
            database="postgres",
            user="postgres",
            password="Kavitha123"
        )
        logging.info("successfully connected to database")
        return connection
    except psycopg2.error as e:
        logging.error(f"error connecting to database : {e}")
        sys(exit(1))

#check existing  available users in the db


def get_available_users(connection,username:str) -> Dict[str,int]:
    """
    Check the count of existing users and repositories in the database.

    :param username: GitHub username to check.
    :return: Dictionary with counts of existing users and repositories.
    """
    global GITHUB_PERSONAL_TOKEN
    
    
    counts={'users':0,'repos':0}
    try:
        with connection.cursor() as cursor :
            

            #execute a select 
            cursor.execute(f"Select count(*) from user_data where username=%s;",(username,))
            counts['users']=cursor.fetchone()[0]
            logging.debug(f"exising users count :{counts['users']}")

            #repositories data 
            
            cursor.execute(f"Select count(*) from repositories where username=%s;",(username,))
            counts['repos']=cursor.fetchone()[0]
            #global existing_users---old implementation with global variable
            #existing_users=existing_users[0][0]
            logging.debug(f"exisitng repository count:{counts['repos']}")
    except  psycopg2.Error as e:
        logging.error(f"database query error :{e}")               

    # Close the cursor and connection
    #cursor.close()
    return counts
    



#function to get userdata from github


def get_user_data_git(username:str) -> Optional[Dict]:
    '''API end point to get user data
    make a get request to api
    '''
    global GITHUB_PERSONAL_TOKEN
    URL=f"https://api.github.com/users/{username}"
    print(URL)
    headers = {
        "Authorization": f"Bearer {GITHUB_PERSONAL_TOKEN}",
        "User-Agent": "py-github-project"}
    #logging.info(f"headers:{headers}")
    try: 
        response=requests.get(URL,headers=headers)
        #logging.info(f"response:{response}")
         #check if the request was successful
        if response.status_code == 200:
            logging.info(F"successfully fetched userdata")
            user_data=response.json()
            return (user_data)
            
        
        else: 
            logging.error(f"unable to fetch the data for user {username}. response:{response}")
            return None
    except requests.RequestException as e:
        logging.error(f"requests exception :{e}")
        return None
    

#function to get repository details 

def get_repository_det_git(username:str,pages_total:int,per_page:int)-> Optional[List[Dict]]:
    '''to get all paginated results
        make a get request to api 

    '''
    global github_personal_token
     
    i=0
    repositories=[] 
    try:
        while i< pages_total:
        #print({i},{pages_total})
        #API endpoint to get repository details
            URL=f"https://api.github.com/users/{username}/repos?type=owner&per_page={per_page}&page={i}"
            #print(URL)
            headers = {
            "Authorization": f"Bearer {GITHUB_PERSONAL_TOKEN}",
            "User-Agent": "py-github-project"}
            response=requests.get(URL,headers=headers)

            #check if response was success
            if response.status_code == 200:
                repository=response.json()
                repository_det=[k for k in repository]
                repositories.extend(repository_det)
                logging.debug(f"fetched page")
                #print(repository_det)
                i=i+1

            else: 
                logging.error(f"unable to fetch repository details for {username}, error:{response}")
                return None
     
        return repositories
    except requests.RequestException as e:
        logging.error( f"Request exception while fetching repositories: {e}")
        return None

#write user data into data base userdata table


def write_user_data(connection,username:str,user_email:Optional[str],location:Optional[str]):
    try:
        with connection.cursor() as cursor:

            cursor.execute(f"insert into user_data(username,email,location) values (%s,%s,%s);",(username,user_email,location))
            connection.commit()
            logging.info(f"data inserted successfully to user_data")

            # Close the cursor and connection
    except psycopg2.Error as e:
            logging.error(f"error while inserting data :{e}")
            


#write repositories into data base


def write_repositories(connection,username:str,repositories:List[Dict]):
    try:

        with connection.cursor() as cursor:
            for k in repositories :
        
                cursor.execute(f"insert into repositories(name,description,languages,username) values (%s,%s,%s,%s);",(k['name'],k['description'],k['language'],username))
                connection.commit()
    
                
        logging.info(f"data inserted successfully to repositories")
    except psycopg2.error as e:
        logging.error(f"error inserting repo details: {e}")
            
            
    


#print the data as output


def print_output(connection,username:str):
    try :
        with connection.cursor() as cursor:
            '''Fetch user details'''
            cursor.execute(f"select username,email from user_data where username=%s;",(username,))
            user_det=cursor.fetchone()
            if user_det:
                print(f"user name :{user_det[0]}")
                print(f"Email :{user_det[1]}")
            else:
                logging.warning(f"No user data found for username '{username}'.")
            '''fetch repo details'''
            cursor.execute(f"select name,description from repositories where username=%s;",(username,))
            repo=cursor.fetchall()
            '''alternative way to print 
            #formatting to print
            #headers=['name','description']
            #define separator
            #separator="|--------------------------------------------------------"
            #print header and separator
            #print(separator)
            #print(f"|{headers[0]:<16}|{headers[1]:<120}|")
            #print(separator)
            '''
            if repo: 
            #printint using pretty table library
                print("Public Repositories:")
        
                #create pretty table object
                table=PrettyTable()
                #define column headers 
                table=PrettyTable(['name','description'])
                
                #loop through the rows and print 
                for row in repo:
                    name,description=row
                        
                    description=description if description else 'N/A'
                    #text wrap the desription
                    wrapped_description=textwrap.wrap( description,width=120)
                    '''altrernative way of printing 
                    #print(wrapped_description)
                    #print for description 120 letters
                    #print(f"|{name:<16} | {wrapped_description[0] :<120}|")'''
                    # Add the first line with the repository name
                    table.add_row([name,wrapped_description[0]])
                    #if the description is >120 print with no value in name
                    for line in wrapped_description[1:]:
                        #print(f"|{'':<16}|{line:<120}|")
                        table.add_row(['',line])
                    
                    
                print(table)
            else:
                logging.info(f"No repositories found for user '{username}'.")
    except psycopg2.Error as e:
        logging.error(f"Error fetching data for output: {e}")
                



def process_user_repos(connection,username:str='',per_page:int=3):
    userdata=get_user_data_git(username)
    #print(userdata)
    #print(userdata['public_repos'])
    total_pages=userdata['public_repos']
    pages_total=math.ceil(total_pages/per_page) #if total_pages % per_page == 0 else (total_pages/per_page) + 1
    repositories=get_repository_det_git(username,pages_total,per_page)
    #print(repositories) 
    write_repositories(connection,username,repositories)
    print_output(connection,username)

#main
def main():
    """
    Main entry point of the script.
    """
    #input user name 
    username=input("enter github username:").strip()
    if not username:
        logging.error("No user name entered ,exiting")
        sys.exit(1)
    global github_personal_token
    per_page=3
    logging.info(f"username entered is :{username}")

    # Initialize database connection
    connection = get_database_connection()

    try : 
        counts=get_available_users(connection,username)
        existing_users = counts['users']
        existing_repos = counts['repos']
        #print(existing_users,existing_repos)
        if existing_users>0:
            logging.info(f"user {username} already exist in user table")
            if existing_repos>0:
                logging.info(f"user {username} already exist in repositories")
                print_output(connection,username)
            else:
                logging.info(f"No repositories found for user '{username}'. Fetching from GitHub...")
                process_user_repos(connection,username,per_page)
            
        else:
            
        
            userdata=get_user_data_git(username)
            if userdata :
                email=userdata.get('email','NA')
                location=userdata.get('location','NA')
                write_user_data(connection,username,email,location)
                process_user_repos(connection,username,per_page)

            else:
                logging.error(f"User '{username}' data could not be fetched from GitHub.")
    
    finally:
        connection.close()

if __name__=="__main__":
    main()