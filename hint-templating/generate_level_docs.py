import os
from jinja2 import Template

os.chdir(os.getcwd()+'/'+os.path.dirname(__file__))
with open('level-hints-template.jinja') as f:
    template = Template(f.read())
for file_name in os.listdir('level-hints'):
    with open(f'level-hints/{file_name}') as f:
        # Split hints in file
        blocks = f.read().split('\n---\n')
    level_name = file_name.split('.')[0]
    jinja_args = {'level_name': level_name,
                'setup': blocks[0].replace('\n<',f'\n{" "*6}<'),
                'destroy': blocks[1].replace('\n<',f'\n{" "*6}<'),
                  'intro': blocks[2].replace('\n<',f'\n{" "*6}<'),
                  'hints': [block.replace('\n<',f'\n{" "*6}<') for block in blocks[3:]]}
    
    render = template.render(**jinja_args)
    with open(f'{os.path.dirname(os.getcwd())}/docs/levels/{level_name}.html', 'w+') as f:
        f.write(render)