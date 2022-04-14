import click
from nethelper import *
from self_healing import *
import matplotlib.pyplot as plt


@click.command()
@click.option("--intent", prompt="Enter an intent", help="intent name")




def cli(intent):
    click.echo("The user intent is - \"%s\"!" % intent)
    if intent.lower() in ["visualize topology","show topology"]:
        draw_topology()
        plt.show()
        print("Topology file generated")
    elif intent.lower() in ['traffic stats', 'switch stats', 'port stats']:
    	print(switch_stats())
    elif intent.lower() in ['highest utilized link']:
    	print(highest_utilized_link())
    elif intent.lower() in ['highest utilized switch']:
    	print(highest_utilized_switch())
    elif intent.lower() in ["heal network","self healing","self heal"]:
        print(heal_my_network())


if __name__ == '__main__':
    cli()
