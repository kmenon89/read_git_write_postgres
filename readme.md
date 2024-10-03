Get user from github , get all the public repository details from the user, load it in to postgress and print

if user does not already exist in postgress then do the above

steps:

create a table in postgres with username and repository name and description  as Userdata
get username as input 
check input if exist in userdata field username 
if exists exit with message user exist 
else connect to github
use api with input parameter as username?
read the output
store details from output in the table userdata 
read data from postgres and then print
print repostiry name 


# List running containers
docker ps

# List all containers (including stopped ones)
docker ps -a

# Restart the container
docker restart <container_name_or_ID>

# View logs to confirm PostgreSQL is running
docker logs <container_name_or_ID>


# Directly access PostgreSQL from host
docker exec -it <container_name_or_ID> psql -U <username>

connet to git :
cd path/to/your/project
git init
git add . 
git status 
gitm commit -a 

TBD:

1. connections needs to be standardised 
2. upload to github 

