/*
 * Copyright 2018-2019 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import * as dagre from 'dagre';
import { Template, Workflow } from '../../third_party/argo-ui/argo_template';
import { color } from '../Css';
import { Constants } from './Constants';
import { logger } from './Utils';
import { parseTaskDisplayName } from './ParserUtils';

export type nodeType = 'container' | 'resource' | 'dag' | 'unknown';

export interface KeyValue<T> extends Array<any> {
  0?: string;
  1?: T;
}

export class SelectedNodeInfo {
  public args: string[];
  public command: string[];
  public condition: string;
  public image: string;
  public inputs: Array<KeyValue<string>>;
  public nodeType: nodeType;
  public outputs: Array<KeyValue<string>>;
  public volumeMounts: Array<KeyValue<string>>;
  public resource: Array<KeyValue<string>>;

  constructor() {
    this.args = [];
    this.command = [];
    this.condition = '';
    this.image = '';
    this.inputs = [[]];
    this.nodeType = 'unknown';
    this.outputs = [[]];
    this.volumeMounts = [[]];
    this.resource = [[]];
  }
}

export function _populateInfoFromTemplate(
  info: SelectedNodeInfo,
  template?: Template,
): SelectedNodeInfo {

  if (!template) {
    return info;
  }

  info.nodeType = 'container';
  if (template['spec']['steps']){
    info.args = template['spec']['steps'][0]['args'];
    info.command = template['spec']['steps'][0]['command'];
    info.image = template['spec']['steps'][0]['image'];
  }

  if (template['spec']['params'])
    info.inputs = (template['spec']['params'] || []).map((p: any) => [p['name'], p['value'] || '']);
  if (template['spec']['results'])
    info.outputs = (template['spec']['results'] || []).map((p: any) => {return [p['name'], p['description'] || '']});

  return info;
}

export function createGraph(workflow: any): dagre.graphlib.Graph {
  const graph = new dagre.graphlib.Graph();
  graph.setGraph({});
  graph.setDefaultEdgeLabel(() => ({}));

  const templates = new Map<string, { templateType: string; template: any }>();

  let pipelineTemplateId = workflow[0]['metadata']['name'];

  // Iterate through the workflow's templates to construct a map which will be used to traverse and
  // construct the graph
  for (const template of workflow) {

    if (template['kind'] == 'Task' || template['kind'] == 'Condition'){
      templates.set(template['metadata']['name'], {templateType: 'task', template})
    }
    else if (template['kind'] == 'Pipeline'){
      templates.set(template['metadata']['name'], {templateType: 'pipeline', template})
      pipelineTemplateId = template['metadata']['name']
    } else {
      throw new Error(
        `Unknown template kind: ${template['kind']} on workflow template: ${template['metadata']['name']}`,
      );
    }
  }

  buildTektonDag(graph, pipelineTemplateId, templates);
  return graph;
}

function buildTektonDag(
  graph: dagre.graphlib.Graph,
  pipelineId: string,
  templates: Map<string, { templateType: string; template: any }>
  ): void {

  const pipeline = templates.get(pipelineId)!['template']
  const tasks = pipeline['spec']['tasks']

  for (const task of tasks){

    const taskName = task['name'];

    // Checks for dependencies mentioned in the runAfter section of a task and then checks for dependencies based
    // on task output being passed in as parameters
    if (task['runAfter'])
      task['runAfter'].forEach((depTask: any)=> {
        graph.setEdge(depTask, taskName)
      });

    // Adds any dependencies that arise from Conditions and tracks these dependencies to make sure they aren't duplicated in the case that
    // the Condition and the base task use output from the same dependency
    const conditionDeps = []
    for (const condition of (task['conditions'] || [])){
      for (const condParam of (condition['params'] || [])) {
        const conditionDep = /^(\$\(tasks\.[^.]*)/.exec(condParam['value']);  // A regex for checking if the params are being passed from another task
        if (conditionDep){
          const parentTask = conditionDep[0].substring(conditionDep[0].indexOf(".") + 1)
          graph.setEdge(parentTask, condition['conditionRef'])
          graph.setEdge(condition['conditionRef'], taskName)

          const condInfo = new SelectedNodeInfo();
          _populateInfoFromTemplate(condInfo, templates.get(taskName)!['template'])
      
          // Add a node for the Condition itself
          graph.setNode(condition['conditionRef'], {
            bgColor: task.when ? 'cornsilk' : undefined,
            height: Constants.NODE_HEIGHT,
            condInfo,
            label: condition['conditionRef'],
            width: Constants.NODE_WIDTH,
          })
        }
      }
    }

    for (const params of task['params']) {
      const searchDep = /^(\$\(tasks\.[^.]*)/.exec(params['value']);  // A regex for checking if the params are being passed from another task
      if (searchDep){
        const parentTask = searchDep[0].substring(searchDep[0].indexOf(".") + 1)
        graph.setEdge(parentTask, taskName)
      }
    }

    // Add the info for this node
    const info = new SelectedNodeInfo();
    _populateInfoFromTemplate(info, templates.get(taskName)!['template'])

    graph.setNode(taskName, {
      bgColor: task.when ? 'cornsilk' : undefined,
      height: Constants.NODE_HEIGHT,
      info,
      label: taskName,
      width: Constants.NODE_WIDTH,
    })
  }
}
