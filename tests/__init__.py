from unmagic import autouse

from .fixtures import package_patches

autouse(package_patches, __file__)
