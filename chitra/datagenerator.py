# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/03_datagenerator.ipynb (unless otherwise specified).

__all__ = ['get_filenames', 'get_label', 'ImageSizeList', 'LabelEncoder', 'Dataset']

# Cell
import tensorflow as tf
import numpy as np
from glob import glob
import random
import os
import pathlib
from functools import partial
from typing import Union

from .image import read_image, resize_image

# Cell
def get_filenames(root_dir):
        root_dir = pathlib.Path(root_dir)
        return glob(str(root_dir/'*'))

def get_label(filename):
    return filename.split('/')[-2]


# Cell
class ImageSizeList():
    def __init__(self, img_sz_list=None):

        if isinstance(img_sz_list, (list, tuple)):
            if len(img_sz_list)!=0 and not isinstance(img_sz_list[0], (list, tuple)):
                img_sz_list = [img_sz_list][:]

        self.start_size = None
        self.last_size = None
        self.curr_size = None
        self.img_sz_list = img_sz_list

        try:
            self.start_size = img_sz_list[0]
            self.last_size = img_sz_list[-1]
            self.curr_size = img_sz_list[0]
        except (IndexError, TypeError) as e:
            print('No item present in the image size list')
            self.curr_size = None # no item present in the list


    def get_size(self):
        img_sz_list = self.img_sz_list
        try:
            self.curr_size = img_sz_list.pop(0)
        except (IndexError, AttributeError) as e:
            print(f'Returning the last set size which is: {self.curr_size}')

        return self.curr_size

# Cell
class LabelEncoder():
    def __init__(self, labels):
        self.labels = labels
        self.label_to_idx = {label: i for i, label in enumerate(self.labels)}

    def encode(self, label):
        return self.label_to_idx[label]

# Cell
class Dataset():
    MAPPINGS = {
        'PY_TO_TF': {str:tf.string, int:tf.int32, float:tf.float32},

        }

    def __init__(self, root_dir, image_size=[], transforms=None, default_encode=True, **kwargs):
        self.get_filenames = get_filenames
        self.read_image = read_image
        self.get_label = get_label
        self.transforms = transforms

        self.root_dir = root_dir
        self.default_encode = default_encode
        self.filenames = self.get_filenames(root_dir)
        self.num_files = len(self.filenames)
        self.image_size = image_size
        self.img_sz_list= ImageSizeList(self.image_size[:])

        self.labels = kwargs.get('labels', self.get_labels())


    def __len__(self): return len(self.filenames)


    def _process(self, filename):
        image = self.read_image(filename)
        label = self.get_label(filename)
        return image, label


    def _reload(self):
        self.filenames  = self.get_filenames(self.root_dir)
        self.num_files = len(self.filenames)
        self.img_sz_list = ImageSizeList(None or self.image_size[:])
        self.labels = self.get_labels()

    def _capture_return_types(self):
        return_types = []
        for e in self.generator():
            outputs = e
            break
        if isinstance(outputs, tuple):
            for ret_type in outputs:
                return_types.append(
                    ret_type.dtype if tf.is_tensor(ret_type) else Dataset.MAPPINGS['PY_TO_TF'][type(ret_type)]
                )
        else:
            return_types.append(
                ret_type.dtype if tf.is_tensor(ret_type) else Dataset.MAPPINGS['PY_TO_TF'][type(ret_type)]
            )
        return tuple(return_types)


    def __getitem__(self, idx):
        filename = self.filenames[idx]
        return self._process(filename)

    def update_component(self, component_name, new_component, reload=True):
        setattr(self, component_name, new_component)
        print(f'{component_name} updated with {new_component}')
        self._reload()


    def get_labels(self):
        # get labels should also update self.num_classes
        root_dir = self.root_dir
        labels = set()
        folders = glob(f'{root_dir}/*')
        for folder in folders:
            labels.add(os.path.basename(folder))

        labels = sorted(labels)
        self.NUM_CLASSES = len(labels)
        self.label_to_idx = {label:i for i, label in enumerate(labels)}

        return labels

    def label_encoder(self, label): return self.label_to_idx[label]


    def generator(self, shuffle=False):
        if shuffle: random.shuffle(self.filenames)
        img_sz = self.img_sz_list.get_size()
        n = len(self.filenames)
        for i in range(n):
            image, label = self.__getitem__(i)
            if img_sz: image = resize_image(image, img_sz)
            if self.transforms: image = self.transforms(image)
            if self.default_encode is True:
                label = self.label_encoder(label)
            yield image, label


    def get_tf_dataset(self, output_shape=None, shuffle=True):
        return_types = self._capture_return_types()
        self._reload()
        generator = partial(self.generator, shuffle=shuffle)
        datagen = tf.data.Dataset.from_generator(
            generator,
            return_types,
            output_shape
        )

        return datagen