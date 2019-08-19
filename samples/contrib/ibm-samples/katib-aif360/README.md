# Training PyTorch models using Katib and integrate with AIF360 fairness check

This pipeline will train a PyTorch gender classification model using [Katib](https://github.com/kubeflow/katib). Then we apply [AI Fairness 360](https://github.com/IBM/AIF360) to check for any bias once the model is trained and stored.
[AI Fairness 360](https://github.com/IBM/AIF360) is very useful on providing various fairness metrics on a model

## Instructions

1. Upload the pytorchWorker template in the Katib platform. The example templates are under the `katib-template` directory.

2. Compile the pipeline with `python katib-aif360.py`

3. Upload the pipeline `katib-aif360.py.tar.gz` to KubeFlow pipeline, then execute it with the parameters and Job template you want.

## Parameters
- **studyjob_name**: Name of the Katib Studyjob, it has to be unique among the cluster. Default: ptjob-example-katib-run
- **optimization_type**: The direction you want to optimize the objective metrics. Default: maximize
- **objective_value_name**: The objective tensor value you want to optimize. Default: accuracy
- **optimization_goal**: The optimization goal value. Default: 0.99
- **request_count**: Number of HPO sets to run. Default: 1
- **metrics_names**: Metrics names for each training job. Default: accuracy
- **parameter_configs**: The HPO configuration. Default: [{"name":"--dummy","parametertype":"int","feasible":{"min":"10","max":"99"}}]
- **nas_config**: Neural architecture search config for reinforcement learning. Default: ''
- **worker_template_path**: Katib worker Job template. Default: pytorchWorker.yaml
- **metrics_collector_template_path**: Katib Metrics template. Default: ''
- **suggestion_spec**: Algorithm spec for each HPO run. Default: {"suggestionAlgorithm":"random","requestNumber":1}
- **studyjob_timeout_minutes**: Maximum time allowed for the studyjob in minutes. Default: 120
- **delete_finished_job**: Delete studyjob when complete. Default: True
- **model_class_file**: PyTorch model file for this pipeline. Default: PyTorchModel.py
- **model_class_name**: PyTorch model class for this pipeline. Default: ThreeLayerCNN
- **feature_testset_path**: Path to the processed test data. Default: processed_data/X_test.npy
- **label_testset_path**: Path to the processed test labels. Default: processed_data/y_test.npy
- **protected_label_testset_path**: Path to the processed protected labels. processed_data/p_test.npy
- **favorable_label**: Favorable outcome for the this model. Default: 0.0
- **unfavorable_label**: Unfavorable outcome for the this model. Default: 1.0
- **privileged_groups**: Privileged feature group. Default: [{'race': 0.0}]
- **unprivileged_groups**: Unprivileged feature group. Default: [{'race': 4.0}]
