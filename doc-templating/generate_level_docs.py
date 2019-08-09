import os
from jinja2 import Template

os.chdir(os.getcwd()+'/'+os.path.dirname(__file__))
with open('level-template.jinja') as f:
    template = Template(f.read())
for file_name in os.listdir('level-hints'):
    with open(f'level-hints/{file_name}') as f:
        blocks = f.read().split('\n---\n')
    level_name = file_name.split('.')[0]
    jinja_args = {'level_name': level_name,
                  'intro': blocks[0],
                  'hints': blocks[1:]}
    render = template.render(**jinja_args)
    with open(f'{os.path.dirname(os.getcwd())}/docs/levels/{level_name}.html', 'w+') as f:
        f.write(render)
