from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'a8ed7afe9a1b'
down_revision = '4018c75d15e0'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('bid', schema=None) as batch_op:
        # No need to drop unnamed constraints in SQLite
        batch_op.add_column(sa.Column('auction_id', sa.Integer(), nullable=True))  # Add as nullable first
        batch_op.create_foreign_key('fk_bid_auction', 'auction', ['auction_id'], ['id'])

    # Update existing records if necessary, then alter column to NOT NULL
    op.execute('UPDATE bid SET auction_id = 1 WHERE auction_id IS NULL')  # Example default value
    with op.batch_alter_table('bid', schema=None) as batch_op:
        batch_op.alter_column('auction_id', nullable=False)

def downgrade():
    with op.batch_alter_table('bid', schema=None) as batch_op:
        batch_op.drop_constraint('fk_bid_auction', type_='foreignkey')
        batch_op.drop_column('auction_id')
