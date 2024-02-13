# -*- coding: utf-8 -*-
"""Machine Learning Pipeline_Fake News Detection with Vectorization, Embedding, and Bidirectional LSTM.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1pGc_MQcxAId_DWiRl6oViOzirRZ4f6S1

# **Project Machine Learning Pipeline - Fake News Detection with Vectorization, Embedding, and Bidirectional LSTM Method**
"""

!pip install tfx tensorflow_model_analysis

#import library
import tensorflow as tf
from tfx.components import CsvExampleGen, StatisticsGen, SchemaGen, ExampleValidator, Transform, Trainer, Tuner
from tfx.proto import example_gen_pb2, trainer_pb2, pusher_pb2
from tfx.orchestration.experimental.interactive.interactive_context import InteractiveContext
from tfx.components import Transform, Trainer, Tuner, Evaluator, Pusher
import os
import pandas as pd
import tensorflow_model_analysis as tfma
from tfx.dsl.components.common.resolver import Resolver
from tfx.dsl.input_resolution.strategies.latest_blessed_model_strategy import LatestBlessedModelStrategy
from tfx.types import Channel
from tfx.types.standard_artifacts import Model, ModelBlessing
import tensorflow_model_analysis as tfma

"""# **Atur Variabel & Dataset**"""

PIPELINE_ROOT = 'pipeline'
METADATA_PATH = 'fake-detect-tfdv-schema'
SERVING_MODEL_DIR = 'serving_model_dir'

true_df = pd.read_csv('/content/True.csv')
true_df

fake_df = pd.read_csv('/content/Fake.csv')
fake_df

# Merger dataset true dan fake
data_path = 'data'

true_df['class'] = 1
fake_df['class'] = 0

news_df = pd.concat([true_df, fake_df], axis=0)

news_df = news_df.drop([
    'title',
    'date',
    'subject'
], axis=1)

news_df = news_df.rename(columns={'class': 'is_real'})
if not os.path.exists(data_path):
    os.makedirs(data_path)

news_df.to_csv(os.path.join(data_path, "NEWS.csv"), index=False)

DATA_ROOT = 'data'

interactive_context = InteractiveContext(pipeline_root = PIPELINE_ROOT)

"""# **Data Ingestion**"""

output = example_gen_pb2.Output(
    split_config = example_gen_pb2.SplitConfig(splits = [
        example_gen_pb2.SplitConfig.Split(name = "train", hash_buckets = 8),
        example_gen_pb2.SplitConfig.Split(name = "eval", hash_buckets = 2)
    ])
)

example_gen = CsvExampleGen(input_base = DATA_ROOT, output_config = output)
interactive_context.run(example_gen)

"""# **Data Validation**"""

# Menampilkan summary stat
stat_gen = StatisticsGen(examples=example_gen.outputs['examples'])
interactive_context.run(stat_gen)

interactive_context.show(stat_gen.outputs['statistics'])

# Schema
schema_gen = SchemaGen(statistics=stat_gen.outputs['statistics'])
interactive_context.run(schema_gen)

# Validator (untuk deteksi anomali based on sum stat dan schema pada data)
eg_validator = ExampleValidator(statistics=stat_gen.outputs['statistics'],
                                schema=schema_gen.outputs['schema'])
interactive_context.run(eg_validator)

interactive_context.show(eg_validator.outputs["anomalies"])

# Tidak ada anomali pada data

"""# **Data Preprocessing**"""

TRANSFORM_MODULE_FILE = "news_detect_transform.py"

# Commented out IPython magic to ensure Python compatibility.
# %%writefile {TRANSFORM_MODULE_FILE}
# 
# import string
# import tensorflow as tf
# import tensorflow_transform as tft
# 
# LABEL_KEY = "is_real"
# FEATURE_KEY = "text"
# 
# 
# def transformed_name(key):
#     return f"{key}_xf"
# 
# 
# def preprocessing_fn(inputs):
#     outputs = dict()
# 
#     outputs[transformed_name(FEATURE_KEY)] = tf.strings.lower(
#         inputs[FEATURE_KEY]
#     )
#     outputs[transformed_name(LABEL_KEY)] = tf.cast(inputs[LABEL_KEY], tf.int64)
# 
#     return outputs

transform = Transform(
    examples=example_gen.outputs["examples"],
    schema=schema_gen.outputs["schema"],
    module_file=os.path.abspath(TRANSFORM_MODULE_FILE)
)
interactive_context.run(transform)

"""# **Model Hyperparameter Tuner**"""

TUNER_MODULE_FILE = "news_detect_tuner.py"

# Commented out IPython magic to ensure Python compatibility.
# %%writefile {TUNER_MODULE_FILE}
# import keras_tuner as kt
# import tensorflow as tf
# import tensorflow_transform as tft
# from typing import NamedTuple, Dict, Text, Any
# from keras_tuner.engine import base_tuner
# from tensorflow.keras import layers
# from tfx.components.trainer.fn_args_utils import FnArgs
# 
# 
# LABEL_KEY = "is_real"
# FEATURE_KEY = "text"
# NUM_EPOCHS = 3
# 
# TunerFnResult = NamedTuple("TunerFnResult", [
#     ("tuner", base_tuner.BaseTuner),
#     ("fit_kwargs", Dict[Text, Any]),
# ])
# 
# early_stopping_callback = tf.keras.callbacks.EarlyStopping(
#     monitor="val_binary_accuracy",
#     mode="max",
#     verbose=1,
#     patience=10,
# )
# 
# 
# def transformed_name(key):
#     return f"{key}_xf"
# 
# 
# def gzip_reader_fn(filenames):
#     return tf.data.TFRecordDataset(filenames, compression_type="GZIP")
# 
# 
# def input_fn(file_pattern, tf_transform_output, num_epochs, batch_size=64):
#     transform_feature_spec = (
#         tf_transform_output.transformed_feature_spec().copy()
#     )
# 
#     dataset = tf.data.experimental.make_batched_features_dataset(
#         file_pattern=file_pattern,
#         batch_size=batch_size,
#         features=transform_feature_spec,
#         reader=gzip_reader_fn,
#         num_epochs=num_epochs,
#         label_key=transformed_name(LABEL_KEY),
#     )
# 
#     return dataset
# 
# 
# def model_builder(hp, vectorizer_layer):
#     num_hidden_layers = hp.Choice(
#         "num_hidden_layers", values=[1, 2]
#     )
#     embed_dims = hp.Int(
#         "embed_dims", min_value=16, max_value=128, step=32
#     )
#     lstm_units= hp.Int(
#         "lstm_units", min_value=32, max_value=128, step=32
#     )
#     dense_units = hp.Int(
#         "dense_units", min_value=32, max_value=256, step=32
#     )
#     dropout_rate = hp.Float(
#         "dropout_rate", min_value=0.1, max_value=0.5, step=0.1
#     )
#     learning_rate = hp.Choice(
#         "learning_rate", values=[1e-2, 1e-3, 1e-4]
#     )
# 
#     inputs = tf.keras.Input(
#         shape=(1,), name=transformed_name(FEATURE_KEY), dtype=tf.string
#     )
# 
#     x = vectorizer_layer(inputs)
#     x = layers.Embedding(input_dim=5000, output_dim=embed_dims)(x)
#     x = layers.Bidirectional(layers.LSTM(lstm_units))(x)
# 
#     for _ in range(num_hidden_layers):
#         x = layers.Dense(dense_units, activation=tf.nn.relu)(x)
#         x = layers.Dropout(dropout_rate)(x)
# 
#     outputs = layers.Dense(1, activation=tf.nn.sigmoid)(x)
# 
#     model = tf.keras.Model(inputs=inputs, outputs=outputs)
# 
#     model.compile(
#         optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
#         loss=tf.keras.losses.BinaryCrossentropy(from_logits=True),
#         metrics=["binary_accuracy"],
#     )
# 
#     return model
# 
# 
# def tuner_fn(fn_args: FnArgs):
#     tf_transform_output = tft.TFTransformOutput(fn_args.transform_graph_path)
# 
#     train_set = input_fn(
#         fn_args.train_files[0], tf_transform_output, NUM_EPOCHS
#     )
#     eval_set = input_fn(
#         fn_args.eval_files[0], tf_transform_output, NUM_EPOCHS
#     )
# 
#     vectorizer_dataset = train_set.map(
#         lambda f, l: f[transformed_name(FEATURE_KEY)]
#     )
# 
#     vectorizer_layer = layers.TextVectorization(
#         max_tokens=5000,
#         output_mode="int",
#         output_sequence_length=500,
#     )
#     vectorizer_layer.adapt(vectorizer_dataset)
# 
#     tuner = kt.Hyperband(
#         hypermodel=lambda hp: model_builder(hp, vectorizer_layer),
#         objective=kt.Objective('binary_accuracy', direction='max'),
#         max_epochs=NUM_EPOCHS,
#         factor=3,
#         directory=fn_args.working_dir,
#         project_name="kt_hyperband",
#     )
# 
#     return TunerFnResult(
#         tuner=tuner,
#         fit_kwargs={
#             "callbacks": [early_stopping_callback],
#             "x": train_set,
#             "validation_data": eval_set,
#             "steps_per_epoch": fn_args.train_steps,
#             "validation_steps": fn_args.eval_steps,
#         },
#     )

tuner = Tuner(
    module_file=os.path.abspath(TUNER_MODULE_FILE),
    examples=transform.outputs["transformed_examples"],
    transform_graph=transform.outputs["transform_graph"],
    schema=schema_gen.outputs["schema"],
    train_args=trainer_pb2.TrainArgs(splits=["train"], num_steps=800),
    eval_args=trainer_pb2.EvalArgs(splits=["eval"], num_steps=400),
)
interactive_context.run(tuner)

"""# **Model Development**"""

TRAINER_MODULE_FILE = "news_detect_trainer.py"

# Commented out IPython magic to ensure Python compatibility.
# %%writefile {TRAINER_MODULE_FILE}
# import os
# import tensorflow as tf
# import tensorflow_transform as tft
# import tensorflow_hub as hub
# from tensorflow.keras import layers
# from tfx.components.trainer.fn_args_utils import FnArgs
# 
# 
# LABEL_KEY = "is_real"
# FEATURE_KEY = "text"
# 
# 
# def transformed_name(key):
#     return f"{key}_xf"
# 
# 
# def gzip_reader_fn(filenames):
#     return tf.data.TFRecordDataset(filenames, compression_type="GZIP")
# 
# 
# def input_fn(file_pattern, tf_transform_output, num_epochs, batch_size=64):
#     transform_feature_spec = (
#         tf_transform_output.transformed_feature_spec().copy()
#     )
# 
#     dataset = tf.data.experimental.make_batched_features_dataset(
#         file_pattern=file_pattern,
#         batch_size=batch_size,
#         features=transform_feature_spec,
#         reader=gzip_reader_fn,
#         num_epochs=num_epochs,
#         label_key=transformed_name(LABEL_KEY),
#     )
# 
#     return dataset
# 
# 
# def model_builder(vectorizer_layer, hp):
#     inputs = tf.keras.Input(
#         shape=(1,), name=transformed_name(FEATURE_KEY), dtype=tf.string
#     )
# 
#     x = vectorizer_layer(inputs)
#     x = layers.Embedding(input_dim=5000, output_dim=hp["embed_dims"])(x)
#     x = layers.Bidirectional(layers.LSTM(hp["lstm_units"]))(x)
# 
#     for _ in range(hp["num_hidden_layers"]):
#         x = layers.Dense(hp["dense_units"], activation=tf.nn.relu)(x)
#         x = layers.Dropout(hp["dropout_rate"])(x)
# 
#     outputs = layers.Dense(1, activation=tf.nn.sigmoid)(x)
# 
#     model = tf.keras.Model(inputs=inputs, outputs = outputs)
# 
#     model.compile(
#         optimizer=tf.keras.optimizers.Adam(learning_rate=hp["learning_rate"]),
#         loss=tf.keras.losses.BinaryCrossentropy(),
#         metrics=[tf.keras.metrics.BinaryAccuracy()],
#     )
# 
#     model.summary()
# 
#     return model
# 
# 
# def _get_serve_tf_example_fn(model, tf_transform_output):
#     model.tft_layer = tf_transform_output.transform_features_layer()
# 
#     @tf.function
#     def serve_tf_examples_fn(serialized_tf_examples):
#         feature_spec = tf_transform_output.raw_feature_spec()
#         feature_spec.pop(LABEL_KEY)
# 
#         parsed_features = tf.io.parse_example(
#             serialized_tf_examples, feature_spec
#         )
#         transformed_features = model.tft_layer(parsed_features)
# 
#         # get predictions using transformed features
#         return model(transformed_features)
# 
#     return serve_tf_examples_fn
# 
# 
# def run_fn(fn_args: FnArgs):
#     hp = fn_args.hyperparameters["values"]
#     log_dir = os.path.join(os.path.dirname(fn_args.serving_model_dir), "logs")
# 
#     tensorboard_callback = tf.keras.callbacks.TensorBoard(
#         log_dir=log_dir, update_freq="batch"
#     )
#     early_stopping_callback = tf.keras.callbacks.EarlyStopping(
#         monitor="val_binary_accuracy",
#         mode="max",
#         verbose=1,
#         patience=10,
#     )
#     model_checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
#         fn_args.serving_model_dir,
#         monitor="val_binary_accuracy",
#         mode="max",
#         verbose=1,
#         save_best_only=True,
#     )
#     callbacks = [
#         tensorboard_callback,
#         early_stopping_callback,
#         model_checkpoint_callback
#     ]
# 
#     tf_transform_output = tft.TFTransformOutput(fn_args.transform_graph_path)
# 
#     train_set = input_fn(
#         fn_args.train_files, tf_transform_output, hp["tuner/epochs"]
#     )
#     eval_set = input_fn(
#         fn_args.eval_files, tf_transform_output, hp["tuner/epochs"]
#     )
# 
#     vectorizer_dataset = train_set.map(
#         lambda f, l: f[transformed_name(FEATURE_KEY)]
#     )
# 
#     vectorizer_layer = layers.TextVectorization(
#         max_tokens=5000,
#         output_mode="int",
#         output_sequence_length=500,
#     )
#     vectorizer_layer.adapt(vectorizer_dataset)
# 
#     model = model_builder(vectorizer_layer, hp)
# 
#     model.fit(
#         x=train_set,
#         steps_per_epoch=fn_args.train_steps,
#         validation_data=eval_set,
#         validation_steps=fn_args.eval_steps,
#         callbacks=callbacks,
#         epochs=hp["tuner/epochs"],
#         verbose=1,
#     )
# 
#     signatures = {
#         "serving_default": _get_serve_tf_example_fn(
#             model, tf_transform_output
#         ).get_concrete_function(
#             tf.TensorSpec(
#                 shape=[None],
#                 dtype=tf.string,
#                 name="examples",
#             )
#         )
#     }
# 
#     model.save(
#         fn_args.serving_model_dir,
#         save_format="tf",
#         signatures=signatures
#     )

trainer = Trainer(
    module_file=os.path.abspath(TRAINER_MODULE_FILE),
    examples=transform.outputs["transformed_examples"],
    transform_graph=transform.outputs["transform_graph"],
    schema=schema_gen.outputs["schema"],
    hyperparameters=tuner.outputs['best_hyperparameters'],
    train_args=trainer_pb2.TrainArgs(splits=["train"], num_steps=800),
    eval_args=trainer_pb2.EvalArgs(splits=["eval"], num_steps=400),
)
interactive_context.run(trainer)

"""# **Analisis Model Dengan *Resolver***"""

model_resolver = Resolver(
    strategy_class=LatestBlessedModelStrategy,
    model=Channel(type=Model),
    model_blessing=Channel(type=ModelBlessing),
).with_id("Latest_blessed_model_resolver")

interactive_context.run(model_resolver)

eval_config = tfma.EvalConfig(
    model_specs=[tfma.ModelSpec(label_key="is_real")],
    slicing_specs=[tfma.SlicingSpec()],
    metrics_specs=[
        tfma.MetricsSpec(metrics=[
            tfma.MetricConfig(class_name="ExampleCount"),
            tfma.MetricConfig(class_name="AUC"),
            tfma.MetricConfig(class_name="TruePositives"),
            tfma.MetricConfig(class_name="FalsePositives"),
            tfma.MetricConfig(class_name="TrueNegatives"),
            tfma.MetricConfig(class_name="FalseNegatives"),
            tfma.MetricConfig(class_name="BinaryAccuracy",
                threshold=tfma.MetricThreshold(
                    value_threshold=tfma.GenericValueThreshold(
                        lower_bound={"value": 0.6},
                    ),
                    change_threshold=tfma.GenericChangeThreshold(
                        direction=tfma.MetricDirection.HIGHER_IS_BETTER,
                        absolute={"value": 1e-4},
                    ),
                ),
            ),
        ])
    ]
)

"""# **Evaluasi Model Dengan *Evaluator***"""

evaluator = Evaluator(
    examples=example_gen.outputs["examples"],
    model=trainer.outputs["model"],
    baseline_model=model_resolver.outputs["model"],
    eval_config=eval_config,
)
interactive_context.run(evaluator)

eval_result = evaluator.outputs["evaluation"].get()[0].uri
tfma_result = tfma.load_eval_result(eval_result)
tfma.addons.fairness.view.widget_view.render_fairness_indicator(tfma_result)

"""# **Eksport Model Dengan *Pusher***"""

pusher = Pusher(
    model=trainer.outputs["model"],
    model_blessing=evaluator.outputs["blessing"],
    push_destination=pusher_pb2.PushDestination(
        filesystem=pusher_pb2.PushDestination.Filesystem(
            base_directory=os.path.join(
                SERVING_MODEL_DIR, "news-detection-model"
            ),
        )
    )
)

interactive_context.run(pusher)

!zip -r /content/puth-pipeline.zip /content/pipeline

!zip -r /content/serving_model_dir.zip /content/serving_model_dir/

# Menyimpan requirements yg diperlukan saat running project ini
!pip freeze >> requirements.txt