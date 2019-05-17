Migrate from:

couch0,couch1:2

to

couch0,couch1,couch2:2


Because the shard allocation strategy strongly prefers
keeping more than half of shards in their current location
for shard consistency during the move,
no shards will be moved in this case and consequently the new node will be empty.
