from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import unittest

import numpy as np

from art.utils import load_mnist, projection, random_sphere, to_categorical, least_likely_class
from art.utils import random_targets, get_label_conf, get_labels_np_array, preprocess, master_seed

logger = logging.getLogger('testLogger')

BATCH_SIZE = 10
NB_TRAIN = 100
NB_TEST = 100


class TestUtils(unittest.TestCase):
    def setUp(self):
        # Set master seed
        master_seed(1234)

    def test_master_seed_mx(self):
        import mxnet as mx

        master_seed(1234)
        x = mx.nd.random.uniform(0, 1, shape=(10,)).asnumpy()
        y = mx.nd.random.uniform(0, 1, shape=(10,)).asnumpy()

        master_seed(1234)
        z = mx.nd.random.uniform(0, 1, shape=(10,)).asnumpy()
        self.assertFalse((x == y).any())
        self.assertTrue((x == z).all())

    def test_master_seed_pytorch(self):
        import torch

        master_seed(1234)
        x = torch.randn(5, 5)
        y = torch.randn(5, 5)

        master_seed(1234)
        z = torch.randn(5, 5)
        self.assertFalse((x == y).any())
        self.assertTrue((x == z).all())

    def test_master_seed_py(self):
        import random

        master_seed(1234)
        x = random.getrandbits(128)
        y = random.getrandbits(128)

        master_seed(1234)
        z = random.getrandbits(128)
        self.assertNotEqual(x, y)
        self.assertEqual(z, x)

    def test_master_seed_np(self):
        master_seed(1234)
        x = np.random.uniform(size=10)
        y = np.random.uniform(size=10)

        master_seed(1234)
        z = np.random.uniform(size=10)
        self.assertTrue((x != y).any())
        self.assertTrue((z == x).all())

    def test_master_seed_tf(self):
        import tensorflow as tf
        tf.reset_default_graph()
        master_seed(1234)

        with tf.Session() as sess:
            x = tf.random_uniform(shape=(1, 10))
            y = tf.random_uniform(shape=(1, 10))
            xv, yv = sess.run([x, y])
        tf.reset_default_graph()
        master_seed(1234)

        with tf.Session() as sess:
            z = tf.random_uniform(shape=(1, 10))
            zv = sess.run([z])[0]
        self.assertTrue((xv != yv).any())
        self.assertTrue((zv == xv).all())

    def test_projection(self):
        # Get MNIST
        (x, _), (_, _), _, _ = load_mnist()

        # Probably don't need to test everything
        x = x[:100]
        t = tuple(range(1, len(x.shape)))
        rand_sign = 1 - 2 * np.random.randint(0, 2, size=x.shape)

        x_proj = projection(rand_sign*x, 3.14159, 1)
        self.assertEqual(x.shape, x_proj.shape)
        self.assertTrue(np.allclose(np.sum(np.abs(x_proj), axis=t), 3.14159, atol=10e-8))

        x_proj = projection(rand_sign*x, 3.14159, 2)
        self.assertEqual(x.shape, x_proj.shape)
        self.assertTrue(np.allclose(np.sqrt(np.sum(x_proj**2, axis=t)), 3.14159, atol=10e-8))

        x_proj = projection(rand_sign*x, 0.314159, np.inf)
        self.assertEqual(x.shape, x_proj.shape)
        self.assertEqual(x_proj.min(), -0.314159)
        self.assertEqual(x_proj.max(), 0.314159)

        x_proj = projection(rand_sign*x, 3.14159, np.inf)
        self.assertEqual(x.shape, x_proj.shape)
        self.assertEqual(x_proj.min(), -1.0)
        self.assertEqual(x_proj.max(), 1.0)

    def test_random_sphere(self):
        x = random_sphere(10, 10, 1, 1)
        self.assertEqual(x.shape, (10, 10))
        self.assertTrue(np.all(np.sum(np.abs(x), axis=1) <= 1.0))

        x = random_sphere(10, 10, 1, 2)
        self.assertTrue(np.all(np.linalg.norm(x, axis=1) < 1.0))

        x = random_sphere(10, 10, 1, np.inf)
        self.assertTrue(np.all(np.abs(x) < 1.0))

    def test_to_categorical(self):
        y = np.array([3, 1, 4, 1, 5, 9])
        y_ = to_categorical(y)
        self.assertEqual(y_.shape, (6, 10))
        self.assertTrue(np.all(y_.argmax(axis=1) == y))
        self.assertTrue(np.all(np.logical_or(y_ == 0.0, y_ == 1.0)))

        y_ = to_categorical(y, 20)
        self.assertEqual(y_.shape, (6, 20))

    def test_random_targets(self):
        y = np.array([3, 1, 4, 1, 5, 9])
        y_ = to_categorical(y)

        random_y = random_targets(y, 10)
        self.assertTrue(np.all(y != random_y.argmax(axis=1)))

        random_y = random_targets(y_, 10)
        self.assertTrue(np.all(y != random_y.argmax(axis=1)))

    def test_least_likely_class(self):
        class DummyClassifier():
            @property
            def nb_classes(self):
                return 4

            def predict(self, x):
                fake_preds = [0.1, 0.2, 0.05, 0.65]
                return np.array([fake_preds] * x.shape[0])

        batch_size = 5
        x = np.random.rand(batch_size, 10, 10, 1)
        classifier = DummyClassifier()
        preds = least_likely_class(x, classifier)
        self.assertTrue(preds.shape == (batch_size, classifier.nb_classes))

        expected_preds = np.array([[0, 0, 1, 0]] * batch_size)
        self.assertTrue((preds == expected_preds).all())

    def test_get_label_conf(self):
        y = np.array([3, 1, 4, 1, 5, 9])
        y_ = to_categorical(y)

        logits = np.random.normal(10 * y_, scale=0.1)
        ps = (np.exp(logits).T / np.sum(np.exp(logits), axis=1)).T
        c, l = get_label_conf(ps)

        self.assertEqual(c.shape, y.shape)
        self.assertEqual(l.shape, y.shape)

        self.assertTrue(np.all(l == y))
        self.assertTrue(np.allclose(c, 0.99, atol=1e-2))

    def test_get_labels_np_array(self):
        y = np.array([3, 1, 4, 1, 5, 9])
        y_ = to_categorical(y)

        logits = np.random.normal(1 * y_, scale=0.1)
        ps = (np.exp(logits).T / np.sum(np.exp(logits), axis=1)).T

        labels = get_labels_np_array(ps)
        self.assertEqual(labels.shape, y_.shape)
        self.assertTrue(np.all(labels == y_))

    def test_preprocess(self):
        # Get MNIST
        (x, y), (_, _), _, _ = load_mnist()

        x = (255 * x).astype('int')[:100]
        y = np.argmax(y, axis=1)[:100]

        x_, y_ = preprocess(x, y)
        self.assertEqual(x_.shape, x.shape)
        self.assertEqual(y_.shape, (y.shape[0], 10))
        self.assertEqual(x_.max(), 1.0)
        self.assertEqual(x_.min(), 0)

        (x, y), (_, _), _, _ = load_mnist()

        x = (5 * x).astype('int')[:100]
        y = np.argmax(y, axis=1)[:100]
        x_, y_ = preprocess(x, y, nb_classes=20, max_value=5)
        self.assertEqual(x_.shape, x.shape)
        self.assertEqual(y_.shape, (y.shape[0], 20))
        self.assertEqual(x_.max(), 1.0)
        self.assertEqual(x_.min(), 0)


if __name__ == '__main__':
    unittest.main()
