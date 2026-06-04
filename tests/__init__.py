from unmagic import autouse, fence

from .fixtures import package_patches

autouse(package_patches, __file__)
fence.install(['', 'commcare_cloud', 'tests'])
