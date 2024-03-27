from arguments import get_args_parser
from process_datasets import build_dataset, collate_fn, build_metrics
from transformers import TrainingArguments, ViTForImageClassification
from loss import DistillationTrainer


def get_distillation_training_args(args):

    output_path = args.results + 'distillation-' + args.student_model.split('/')[-1] + '/'

    return TrainingArguments(
        output_dir=output_path,
        logging_dir=output_path + 'logs/',
        per_device_train_batch_size=16,
        evaluation_strategy="steps",
        num_train_epochs=args.epochs,
        save_steps=100,
        eval_steps=50,
        logging_steps=10,
        learning_rate=args.lr,
        weight_decay=args.weight_decay,
        save_total_limit=2,
        remove_unused_columns=False,
        push_to_hub=False,
        load_best_model_at_end=True
    )


def run_distillation(args):
    teacher_model = ViTForImageClassification.from_pretrained(args.results + args.fine_tuned_dir + args.model)

    # print(teacher_model)

    num_labels, training_data, testing_data = build_dataset(True, args, show_details=False)

    compute_metrics = build_metrics(args)

    student_model = ViTForImageClassification.from_pretrained(args.student_model,
                                                              num_labels=num_labels,
                                                              cache_dir=args.model_dir,
                                                              ignore_mismatched_sizes=True)

    # print(student_model)

    distillation_args = get_distillation_training_args(args)

    distillation_trainer = DistillationTrainer(
        teacher_model=teacher_model,
        student_model=student_model,
        args=distillation_args,
        data_collator=collate_fn,
        compute_metrics=compute_metrics,
        train_dataset=training_data,
        eval_dataset=testing_data,
        temperature=5,
        alpha=0.5
    )

    train_results = distillation_trainer.train()

    distillation_trainer.save_model(output_dir=args.results + args.distilled_dir + args.student_model)
    distillation_trainer.log_metrics("train", train_results.metrics)
    distillation_trainer.save_metrics("train", train_results.metrics)
    distillation_trainer.save_state()

    metrics = distillation_trainer.evaluate(testing_data)
    distillation_trainer.log_metrics("eval", metrics)
    distillation_trainer.save_metrics("eval", metrics)


if __name__ == '__main__':
    args = get_args_parser()
    run_distillation(args)
