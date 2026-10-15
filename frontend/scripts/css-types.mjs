import { readdir,readFile,writeFile } from 'node:fs/promises';
import path from 'node:path';
import postcss from 'postcss';
import selectorParser from 'postcss-selector-parser';
async function visit(directory){
  for(const entry of await readdir(directory,{withFileTypes:true})){
    const filename=path.join(directory,entry.name);
    if(entry.isDirectory())await visit(filename);
    else if(entry.isFile()&&entry.name.endsWith('.module.css')){
      const names=new Set();
      const root=postcss.parse(await readFile(filename,'utf8'),{from:filename});
      root.walkRules(rule=>{
        selectorParser(selectors=>selectors.each(selector=>{
          let local=true;
          selector.each(node=>{
            if(node.type==='pseudo'&&(node.value===':global'||node.value===':local')&&!node.nodes?.length){local=node.value===':local';return;}
            const collect=classNode=>{
              let allowed=local;let parent=classNode.parent;
              while(parent&&parent!==selector){
                if(parent.type==='pseudo'&&parent.value===':global'){allowed=false;break;}
                if(parent.type==='pseudo'&&parent.value===':local'){allowed=true;break;}
                parent=parent.parent;
              }
              if(allowed)names.add(classNode.value);
            };
            if(node.type==='class')collect(node);
            else if('walkClasses' in node)node.walkClasses(collect);
          });
        })).processSync(rule.selector);
      });
      const entries=[...names].sort().map(name=>'  readonly '+JSON.stringify(name)+': string;').join('\n');
      await writeFile(filename+'.d.ts','// Generated from local CSS selectors.\ndeclare const styles: {\n'+entries+'\n};\nexport default styles;\n');
    }
  }
}
await visit('src');
