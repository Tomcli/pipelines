// Copyright 2021 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	pb "github.com/kubeflow/pipelines/api/v2alpha1/go"
	"github.com/kubeflow/pipelines/backend/src/v2/compiler/templates"
	"github.com/pkg/errors"
	workflowapi "github.com/tektoncd/pipeline/pkg/apis/pipeline/v1beta1"
)

const (
	rootDagDriverTaskName = "driver-kfp-root"
)

const (
	templateNameExecutorDriver    = "kfp-executor-driver"
	templateNameDagDriver         = "kfp-dag-driver"
	templateNameExecutorPublisher = "kfp-executor-publisher"
)

func CompilePipelineSpec(
	pipelineSpec *pb.PipelineSpec,
	deploymentConfig *pb.PipelineDeploymentConfig,
) (*workflowapi.PipelineRun, error) {

	// validation
	if pipelineSpec.GetPipelineInfo().GetName() == "" {
		return nil, errors.New("Name is empty")
	}

	// initialization
	var workflow workflowapi.PipelineRun
	workflow.APIVersion = "tekton.dev/v1beta1"
	workflow.Kind = "PipelineRun"
	workflow.GenerateName = pipelineSpec.GetPipelineInfo().GetName() + "-"

	spec, err := generateSpec(pipelineSpec, deploymentConfig)
	if err != nil {
		return nil, errors.Wrapf(err, "Failed to generate workflow spec")
	}
	workflow.Spec = *spec

	return &workflow, nil
}

func generateSpec(
	pipelineSpec *pb.PipelineSpec,
	deploymentConfig *pb.PipelineDeploymentConfig,
) (*workflowapi.PipelineRunSpec, error) {
	tasks := pipelineSpec.GetTasks()
	var spec workflowapi.PipelineRunSpec

	// generate helper templates
	// executorDriver := templates.Driver(false)
	// executorDriver.Name = templateNameExecutorDriver
	// dagDriver := templates.Driver(true)
	// dagDriver.Name = templateNameDagDriver
	// executorPublisher := templates.Publisher(common.PublisherType_EXECUTOR)
	// executorPublisher.Name = templateNameExecutorPublisher
	// executorTemplates := templates.Executor(templateNameExecutorDriver, templateNameExecutorPublisher)

	// generate root template
	//var root workflowapi.PipelineRunSpec
	// root.Name = "kfp-root"
	// rootDag := initRootDag(&spec, templateNameDagDriver)
	// root.PipelineSpec = rootDag
	// TODO: make a generic default value
	defaultTaskSpec := `{"taskInfo":{"name":"hello-world-dag"},"inputs":{"parameters":{"text":{"runtimeValue":{"constantValue":{"stringValue":"Hello, World!"}}}}}}`

	spec.Params = []workflowapi.Param{
		{Name: "task-spec",
			Value: workflowapi.ArrayOrString{
				Type:      workflowapi.ParamTypeString,
				StringVal: defaultTaskSpec,
			},
		},
	}

	subDag, err := templates.Dag(&templates.DagArgs{
		Tasks:                &tasks,
		DeploymentConfig:     deploymentConfig,
		ExecutorTemplateName: templates.TemplateNameExecutor,
	})
	if err != nil {
		return nil, err
	}
	//parentContextName := "{{tasks." + rootDagDriverTaskName + ".outputs.parameters." + templates.DriverParamContextName + "}}"
	//root.PipelineSpec.Tasks = append(root.PipelineSpec.Tasks, subDag.Tasks...)

	spec.PipelineSpec = subDag
	// []workflowapi.Template{root, *subDag, *executorDriver, *dagDriver, *executorPublisher}
	// for _, template := range executorTemplates {
	// 	spec.PipelineSpec.Tasks = append(spec.PipelineSpec.Tasks, *template)
	// }
	return &spec, nil
}

// func initRootDag(spec *workflowapi.PipelineRunSpec, templateNameDagDriver string) *workflowapi.PipelineSpec {
// 	root := &workflowapi.PipelineSpec{}
// 	// TODO(Bobgy): shall we pass a lambda "addTemplate()" here instead?
// 	driverTask := &workflowapi.TaskSpec{}
// 	driverTask.Name = rootDagDriverTaskName
// 	driverTask.Template = templateNameDagDriver
// 	rootExecutionName := "kfp-root-{{workflow.name}}"
// 	workflowParameterTaskSpec := "{{workflow.parameters.task-spec}}"
// 	driverType := "DAG"
// 	parentContextName := "" // root has no parent
// 	driverTask.Arguments.Parameters = []workflowapi.Parameter{
// 		{Name: templates.DriverParamExecutionName, Value: &rootExecutionName},
// 		{Name: templates.DriverParamTaskSpec, Value: &workflowParameterTaskSpec},
// 		{Name: templates.DriverParamDriverType, Value: &driverType},
// 		{Name: templates.DriverParamParentContextName, Value: &parentContextName},
// 	}
// 	root.Tasks = append(root.Tasks, *driverTask)
// 	return root
// }
