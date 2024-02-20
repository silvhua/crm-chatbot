python src/app/save_prompt_version.py
aws s3 cp src/app/private/prompts/CoachMcloone.md s3://ownitfit-silvhua
cd ~
source backup-wsl.sh 
cd repositories/GHL-chat