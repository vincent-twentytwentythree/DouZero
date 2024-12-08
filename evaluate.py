import os 
import argparse

from douzero.evaluation.simulation import evaluate

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    'Dou Dizhu Evaluation')
    parser.add_argument('--landlord', type=str,
            default='baselines/douzero_ADP/landlord.ckpt')
    parser.add_argument('--second_hand', type=str,
            default='baselines/sl/second_hand.ckpt')
    parser.add_argument('--pk_dp', type=str,
            default='baselines/sl/pk_dp.ckpt')
    parser.add_argument('--eval_data', type=str,
            default='eval_data.pkl')
    parser.add_argument('--num_workers', type=int, default=5)
    parser.add_argument('--gpu_device', type=str, default='')
    args = parser.parse_args()

    os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_device

    evaluate(args.landlord,
             args.second_hand,
             args.pk_dp,
             args.eval_data,
             args.num_workers)
