from models_utils import ViTForImageClassification, DeiTForImageClassificationWithTeacher
from transformers import ViTImageProcessor, DeiTImageProcessor
from transformers.image_transforms import resize
from transformers.image_utils import PILImageResampling
from utils.attributionUtils import process_attribution
import matplotlib.patches as pat
import matplotlib.pyplot as plt
import glob
import numpy as np
from PIL import Image
import pandas as pd
import seaborn as sns
import warnings

warnings.filterwarnings('ignore')

def visualize(Args):

    outputPath = Args.Visualization.Output
    showImages = Args.Visualization.Show
    saveImages = Args.Visualization.Save

    images = glob.glob("Images/*.JPEG")
    Device = Args.Visualization.Model.Device

    # model_path = get_model_path('FineTuned', Args)
    model_name = Args.Visualization.Model.Name
    if 'distilled' in model_name:
        classifier = DeiTForImageClassificationWithTeacher
        feature_extractor = DeiTImageProcessor
    else:
        classifier = ViTForImageClassification
        feature_extractor = ViTImageProcessor

    model = classifier.from_pretrained(model_name, cache_dir=Args.Visualization.Model.CachePath)

    processor = feature_extractor.from_pretrained(model_name, cache_dir=Args.Visualization.Model.CachePath)

    model.eval()
    model.to(Device)

    for im in images[:3]:

        label = im.split('_')[1].split('.')[0]
        image = Image.open(im)
        factor = 14

        img_resized = resize(np.array(image), size=(224, 224), resample=PILImageResampling.BILINEAR)
        grid_color = [0, 0, 0]
        grid_size = 224 // factor
        img_resized_grid = img_resized.copy()
        img_resized_grid[:, ::grid_size, :] = grid_color
        img_resized_grid[::grid_size, :, :] = grid_color

        fig = plt.figure()
        plt.imshow(img_resized_grid)
        plt.axis('off')
        if  saveImages:
            plt.savefig(outputPath+f"{label}_1_grid")
        if showImages:
            plt.show()
        plt.close(fig)

        inputs = processor(images=image, return_tensors="pt")
        inputs.to(Device)
        outputs = model(**inputs, output_attentions=True, output_hidden_states=True, output_norms=True,
                              output_globenc=True)
        logits = outputs.logits
        predicted_class_idx = logits.argmax(-1).item()
        print(f"Actual: {label.ljust(10, ' ')} Predicted: {model.config.id2label[predicted_class_idx]}")

        patches = process_attribution(outputs.attributions, factor)

        plt.figure(figsize=(7, 7))
        df = pd.DataFrame(patches, columns=np.arange(1, patches.shape[1]+1), index=range(len(patches), 0, -1))
        ax = sns.heatmap(df, cmap="Reds", square=True)
        bottom, top = ax.get_ylim()
        ax.set_ylim(bottom + 0.5, top - 0.5)
        plt.title("GlobEnc", fontsize=16)
        # plt.ylabel("Layer", fontsize=16)
        # plt.xticks(rotation = 90, fontsize=16)
        plt.xticks([])
        # plt.yticks(fontsize=9)
        plt.yticks([])
        plt.gcf().subplots_adjust(bottom=0.2)
        if saveImages:
            plt.savefig(outputPath + f"{label}_3_heatmap")
        if showImages:
            plt.show()

        # print(patches[0])

        mean = np.mean(patches[0])

        attribute_score_per_patch = [1 if patches[0, i] > mean else 0 for i in range(patches.shape[1])]

        # print(len(attribute_score_per_patch))

        img_resized_final = img_resized.copy()
        fig, ax = plt.subplots()
        ax.imshow(img_resized_final)
        if factor > 14:
            factor = 14
        x, y = np.meshgrid(np.arange(0, factor), np.arange(0, factor), indexing='ij')

        for i in range(factor):
            for j in range(factor):
                index = x[i,j]*factor + y[i,j]
                if attribute_score_per_patch[index] == 1:
                    rect = pat.Rectangle((y[i,j] * grid_size, x[i,j] * grid_size), grid_size - 1, grid_size -1, linewidth=1,
                                         edgecolor='r', facecolor='none')

                    ax.add_patch(rect)

        plt.imshow(img_resized_final)
        plt.axis('off')
        if saveImages:
            plt.savefig(outputPath + f"{label}_2_attributes")
        if showImages:
            plt.show()