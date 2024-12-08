checkpoint_dir=$1

landlord_path=$landlord_dir`ls -v "$checkpoint_dir"landlord_weights* | tail -1`
second_hand_path=$second_hand_dir`ls -v "$checkpoint_dir"second_hand_weights* | tail -1`
pk_dp_path=$pk_dp_dir`ls -v "$checkpoint_dir"pk_dp_weights* | tail -1`

echo $landlord_path
echo $second_hand_path
echo $pk_dp_path

mkdir -p most_recent_model

cp $landlord_path most_recent_model/landlord.ckpt
cp $second_hand_path most_recent_model/second_hand.ckpt
cp $pk_dp_path most_recent_model/pk_dp.ckpt
